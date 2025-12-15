import json
import sys
import hmac
import hashlib
from typing import Any

import boto3
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def read_s3_json(s3_uri: str) -> dict[str, Any]:
    if not s3_uri.startswith("s3://"):
        raise ValueError("spec_s3_uri must start with s3://")
    bucket, key = s3_uri.replace("s3://", "", 1).split("/", 1)
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def write_s3_json(s3_uri: str, payload: dict[str, Any]) -> None:
    bucket, key = s3_uri.replace("s3://", "", 1).split("/", 1)
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode("utf-8"))


def _spark_type_to_glue(t: str) -> str:
    t = (t or "").lower()
    if t.startswith("string"):
        return "string"
    if t.startswith("int"):
        return "int"
    if t.startswith("bigint") or t.startswith("long"):
        return "bigint"
    if t.startswith("double") or t.startswith("float") or t.startswith("decimal"):
        return "double"
    if t.startswith("boolean"):
        return "boolean"
    if t.startswith("timestamp"):
        return "timestamp"
    if t.startswith("date"):
        return "date"
    return "string"


def _build_user_key(pepper: str, user_id: int) -> bytes:
    return hmac.new(pepper.encode("utf-8"), str(user_id).encode("utf-8"), hashlib.sha256).digest()


def _tokenize_udf(user_key: bytes):
    def _tokenize(value):
        if value is None:
            return None
        raw = str(value).strip().lower().encode("utf-8")
        return hmac.new(user_key, raw, hashlib.sha256).hexdigest()

    return F.udf(_tokenize)


def load_pepper(secret_id: str) -> str:
    sm = boto3.client("secretsmanager")
    resp = sm.get_secret_value(SecretId=secret_id)
    s = resp.get("SecretString") or ""
    try:
        j = json.loads(s)
        return j.get("pepper") or s
    except Exception:
        return s


def read_input(glue_ctx: GlueContext, spec: dict[str, Any], args: dict[str, str]) -> dict[str, DataFrame]:
    spark = glue_ctx.spark_session
    frames: dict[str, DataFrame] = {}

    for inp in spec.get("inputs", []):
        alias = inp.get("alias") or "a"
        in_type = inp.get("type") or "s3"
        if in_type in ("upload", "s3"):
            s3_uri = inp.get("s3_uri") or args.get("raw_s3_uri")
            fmt = (inp.get("format") or "csv").lower()
            if not s3_uri:
                raise ValueError("Missing s3_uri for input")
            if fmt == "csv":
                df = spark.read.option("header", "true").option("inferSchema", "true").csv(s3_uri)
            elif fmt == "json":
                df = spark.read.option("multiLine", "true").json(s3_uri)
            elif fmt == "parquet":
                df = spark.read.parquet(s3_uri)
            else:
                raise ValueError(f"Unsupported input format for Glue job: {fmt}")
            frames[alias] = df
        elif in_type == "postgres":
            jdbc_url = args["jdbc_url"]
            jdbc_user = args["jdbc_user"]
            jdbc_password = args["jdbc_password"]
            query = inp.get("query")
            schema = inp.get("schema") or "public"
            table = inp.get("table")
            if query:
                dbtable = f"({query}) as q"
            else:
                if not table:
                    raise ValueError("postgres input requires table or query")
                dbtable = f"{schema}.{table}"
            df = (
                spark.read.format("jdbc")
                .option("url", jdbc_url)
                .option("dbtable", dbtable)
                .option("user", jdbc_user)
                .option("password", jdbc_password)
                .option("driver", "org.postgresql.Driver")
                .load()
            )
            frames[alias] = df
        else:
            raise ValueError(f"Unsupported input type: {in_type}")

    if not frames:
        raise ValueError("No inputs provided")
    return frames


def apply_steps(frames: dict[str, DataFrame], spec: dict[str, Any], pepper: str, user_id: int) -> DataFrame:
    df = frames.get("a") or next(iter(frames.values()))
    user_key = _build_user_key(pepper, user_id)
    tok = _tokenize_udf(user_key)

    for step in spec.get("steps", []):
        st = step.get("type")
        if st == "rename":
            mapping = step.get("mapping") or {}
            for old, new in mapping.items():
                df = df.withColumnRenamed(old, new)
        elif st == "cast":
            cols = step.get("columns") or {}
            for col, to_type in cols.items():
                df = df.withColumn(col, F.col(col).cast(to_type))
        elif st == "filter_sql":
            expr = step.get("expr")
            if expr:
                df = df.filter(expr)
        elif st == "dedupe":
            subset = step.get("subset") or []
            if subset:
                df = df.dropDuplicates(subset)
            else:
                df = df.dropDuplicates()
        elif st == "pii":
            mode = step.get("mode") or "tokenize"
            cols = step.get("columns") or []
            for col in cols:
                if mode == "tokenize":
                    df = df.withColumn(col, tok(F.col(col)))
                elif mode == "redact":
                    df = df.withColumn(col, F.lit(None).cast("string"))
                elif mode == "drop":
                    df = df.drop(col)
        elif st == "join":
            left_alias = step.get("left") or "a"
            right_alias = step.get("right")
            how = step.get("how") or "inner"
            on = step.get("on") or []
            if not right_alias or right_alias not in frames:
                raise ValueError("join step missing right alias")
            left_df = df if left_alias == "a" else frames[left_alias]
            right_df = frames[right_alias]
            conds = []
            for pair in on:
                l = pair.get("left")
                r = pair.get("right")
                if l and r:
                    conds.append(left_df[l] == right_df[r])
            if not conds:
                raise ValueError("join step missing on conditions")
            cond = conds[0]
            for c in conds[1:]:
                cond = cond & c
            df = left_df.join(right_df, cond, how=how)
        else:
            # Ignore unknown steps for forwards compatibility
            continue

    return df


def main():
    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "spec_s3_uri",
            "curated_s3_uri",
            "schema_s3_uri",
            "user_id",
            "pepper_secret_id",
            "jdbc_url",
            "jdbc_secret_id",
        ],
    )

    sc = SparkContext()
    glue_ctx = GlueContext(sc)
    job = Job(glue_ctx)
    job.init(args["JOB_NAME"], args)

    spec = read_s3_json(args["spec_s3_uri"])

    sm_secret_id = args.get("jdbc_secret_id") or args["jdbc_secret_id"]
    jdbc_url = args["jdbc_url"]
    db_secret = boto3.client("secretsmanager").get_secret_value(SecretId=sm_secret_id)
    secret_str = db_secret.get("SecretString") or "{}"
    secret_json = json.loads(secret_str) if secret_str.strip().startswith("{") else {}
    jdbc_user = secret_json.get("username") or secret_json.get("DB_USERNAME") or "cointelligence"
    jdbc_password = secret_json.get("password") or secret_json.get("DB_PASSWORD") or ""

    runtime_args = {"jdbc_url": jdbc_url, "jdbc_user": jdbc_user, "jdbc_password": jdbc_password}
    frames = read_input(glue_ctx, spec, runtime_args)

    pepper = load_pepper(args["pepper_secret_id"])
    user_id = int(args["user_id"])

    out_df = apply_steps(frames, spec, pepper, user_id)
    out_df.write.mode("overwrite").parquet(args["curated_s3_uri"])

    schema_payload = {
        "columns": [{"name": f.name, "type": _spark_type_to_glue(f.dataType.simpleString())} for f in out_df.schema.fields],
    }
    write_s3_json(args["schema_s3_uri"], schema_payload)

    job.commit()


if __name__ == "__main__":
    main()


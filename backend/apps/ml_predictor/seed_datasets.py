from apps.ml_predictor.models import Dataset
import os
import tempfile

async def seed_datasets():
    """Load sample datasets into database"""
    print("Seeding sample datasets...")
    
    # Create simple CSV data inline (no external dependencies)
    datasets_to_create = [
        {
            "name": "Iris Flower Classification",
            "description": "Classify iris flowers into 3 species based on measurements",
            "csv_content": """sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3.0,1.4,0.2,setosa
4.7,3.2,1.3,0.2,setosa
4.6,3.1,1.5,0.2,setosa
5.0,3.6,1.4,0.2,setosa
5.4,3.9,1.7,0.4,setosa
4.6,3.4,1.4,0.3,setosa
5.0,3.4,1.5,0.2,setosa
7.0,3.2,4.7,1.4,versicolor
6.4,3.2,4.5,1.5,versicolor
6.9,3.1,4.9,1.5,versicolor
5.5,2.3,4.0,1.3,versicolor
6.5,2.8,4.6,1.5,versicolor
5.7,2.8,4.5,1.3,versicolor
6.3,3.3,4.7,1.6,versicolor
4.9,2.4,3.3,1.0,versicolor
6.3,3.3,6.0,2.5,virginica
5.8,2.7,5.1,1.9,virginica
7.1,3.0,5.9,2.1,virginica
6.3,2.9,5.6,1.8,virginica
6.5,3.0,5.8,2.2,virginica
7.6,3.0,6.6,2.1,virginica
4.9,2.5,4.5,1.7,virginica
7.3,2.9,6.3,1.8,virginica""",
            "rows": 24,
            "columns": 5,
            "column_names": ["sepal_length", "sepal_width", "petal_length", "petal_width", "species"]
        },
        {
            "name": "House Prices Regression",
            "description": "Predict house prices based on features like size, bedrooms, etc.",
            "csv_content": """square_feet,bedrooms,bathrooms,age_years,price
1500,3,2,10,250000
2000,4,2,5,350000
1200,2,1,20,180000
1800,3,2,8,300000
2500,4,3,3,450000
1000,2,1,30,150000
2200,4,2,7,380000
1600,3,2,12,270000
3000,5,3,2,550000
1400,3,1,15,220000
1900,3,2,6,320000
2800,5,4,1,600000
1100,2,1,25,160000
2100,4,3,4,400000
1700,3,2,9,290000
2400,4,3,5,420000""",
            "rows": 16,
            "columns": 5,
            "column_names": ["square_feet", "bedrooms", "bathrooms", "age_years", "price"]
        }
    ]
    
    for ds_info in datasets_to_create:
        try:
            # Always write CSV to temp file to ensure it exists
            filename = ds_info['name'].lower().replace(' ', '_') + ".csv"
            file_path = os.path.join(tempfile.gettempdir(), filename)
            
            with open(file_path, 'w') as f:
                f.write(ds_info['csv_content'])
            
            # Update or create DB record
            existing = await Dataset.get_or_none(name=ds_info['name'])
            
            if existing:
                # Update path just in case temp dir changed
                existing.file_path = file_path
                existing.is_sample = True
                await existing.save()
                print(f"✓ {ds_info['name']} dataset restored (file: {file_path})")
            else:
                await Dataset.create(
                    user_id=1,
                    name=ds_info['name'],
                    description=ds_info['description'],
                    file_path=file_path,
                    rows=ds_info['rows'],
                    columns=ds_info['columns'],
                    column_names=ds_info['column_names'],
                    data_types={col: "float64" if col != "species" else "object" for col in ds_info['column_names']},
                    is_sample=True
                )
                print(f"✓ {ds_info['name']} dataset seeded")
                
        except Exception as e:
            print(f"⚠️ Error seeding {ds_info['name']}: {e}")
    
    print("✓ Sample datasets seeding completed")

export async function consumeSseJson(
  response: Response,
  onData: (data: any) => void
): Promise<void> {
  if (!response.body) throw new Error('No response body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const flushEvent = (raw: string) => {
    const lines = raw.split('\n')
    const dataLines = lines
      .map((l) => l.trimEnd())
      .filter((l) => l.startsWith('data:'))
      .map((l) => l.slice(5).trimStart())
    if (!dataLines.length) return
    const payload = dataLines.join('\n')
    try {
      onData(JSON.parse(payload))
    } catch {
      // ignore malformed event
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      if (rawEvent.trim()) flushEvent(rawEvent)
    }
  }

  if (buffer.trim()) flushEvent(buffer)
}

export async function consumeNdjson(
  response: Response,
  onJson: (data: any) => void
): Promise<void> {
  if (!response.body) throw new Error('No response body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    let newlineIndex
    while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim()
      buffer = buffer.slice(newlineIndex + 1)
      if (!line) continue
      try {
        onJson(JSON.parse(line))
      } catch {
        // ignore malformed line
      }
    }
  }

  if (buffer.trim()) {
    try {
      onJson(JSON.parse(buffer))
    } catch {
      // ignore malformed tail
    }
  }
}


'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type UseSpeechToTextOptions = {
  onTranscript: (text: string) => void
  lang?: string
}

export function useSpeechToText({ onTranscript, lang = 'en-US' }: UseSpeechToTextOptions) {
  const recognitionRef = useRef<any>(null)
  const [isListening, setIsListening] = useState(false)

  const isSupported = useMemo(() => {
    if (typeof window === 'undefined') return false
    return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)
  }, [])

  useEffect(() => {
    if (!isSupported) return

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = lang

    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript
      if (typeof transcript === 'string' && transcript.trim()) onTranscript(transcript)
      setIsListening(false)
    }
    recognition.onerror = () => setIsListening(false)
    recognition.onend = () => setIsListening(false)

    recognitionRef.current = recognition
    return () => {
      try {
        recognition.stop()
      } catch {
        // ignore
      }
      recognitionRef.current = null
    }
  }, [isSupported, lang, onTranscript])

  const start = useCallback(() => {
    if (!isSupported || isListening) return
    try {
      recognitionRef.current?.start()
      setIsListening(true)
    } catch {
      setIsListening(false)
    }
  }, [isSupported, isListening])

  const stop = useCallback(() => {
    if (!isSupported || !isListening) return
    try {
      recognitionRef.current?.stop()
    } finally {
      setIsListening(false)
    }
  }, [isSupported, isListening])

  const toggle = useCallback(() => {
    if (isListening) stop()
    else start()
  }, [isListening, start, stop])

  return { isSupported, isListening, start, stop, toggle }
}


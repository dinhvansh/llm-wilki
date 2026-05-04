'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

type DrawioMessage =
  | { event?: string; xml?: string; modified?: boolean; exit?: boolean }
  | { action?: string; xml?: string; autosave?: 1; title?: string; saveAndExit?: 0 | 1; noExitBtn?: 0 | 1 }

interface DrawioEmbedProps {
  title: string
  xml: string
  onXmlChange: (xml: string) => void
  onEditorEvent?: (eventName: string) => void
  className?: string
}

const DRAWIO_BASE_URL = process.env.NEXT_PUBLIC_DRAWIO_BASE_URL ?? 'http://localhost:8081'

export function DrawioEmbed({ title, xml, onXmlChange, onEditorEvent, className }: DrawioEmbedProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [status, setStatus] = useState('Connecting to self-hosted draw.io...')
  const lastLoadedXmlRef = useRef<string>('')

  const editorUrl = useMemo(
    () => `${DRAWIO_BASE_URL}/?embed=1&proto=json&spin=1&libraries=1&saveAndExit=0&noExitBtn=1&modified=unsavedChanges`,
    [],
  )

  useEffect(() => {
    function postLoad(targetXml: string) {
      const frame = iframeRef.current?.contentWindow
      if (!frame) return
      const message: DrawioMessage = {
        action: 'load',
        xml: targetXml || '<mxGraphModel><root /></mxGraphModel>',
        autosave: 1,
        title,
        saveAndExit: 0,
        noExitBtn: 1,
      }
      frame.postMessage(JSON.stringify(message), '*')
      lastLoadedXmlRef.current = targetXml
      setStatus('Editor loaded')
    }

    function onMessage(event: MessageEvent) {
      if (typeof event.data !== 'string') return
      let payload: Record<string, unknown> | null = null
      try {
        payload = JSON.parse(event.data) as Record<string, unknown>
      } catch {
        return
      }
      const eventName = typeof payload?.event === 'string' ? payload.event : null
      if (!eventName) return
      onEditorEvent?.(eventName)

      if (eventName === 'init' || eventName === 'ready') {
        setIsReady(true)
        postLoad(xml)
        return
      }
      if ((eventName === 'autosave' || eventName === 'save') && typeof payload.xml === 'string') {
        onXmlChange(payload.xml)
        setStatus(eventName === 'save' ? 'Editor save captured' : 'Autosave captured')
        return
      }
      if (eventName === 'exit') {
        setStatus(payload.modified === true ? 'Editor exited with unsaved changes' : 'Editor exited')
      }
    }

    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [onEditorEvent, onXmlChange, title, xml])

  useEffect(() => {
    if (!isReady) return
    if (xml === lastLoadedXmlRef.current) return
    const frame = iframeRef.current?.contentWindow
    if (!frame) return
    const message: DrawioMessage = { action: 'load', xml: xml || '<mxGraphModel><root /></mxGraphModel>', autosave: 1, title, saveAndExit: 0, noExitBtn: 1 }
    frame.postMessage(JSON.stringify(message), '*')
    lastLoadedXmlRef.current = xml
    setStatus('Editor refreshed from latest diagram XML')
  }, [isReady, title, xml])

  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="text-sm font-semibold">Self-hosted draw.io Editor</div>
        <div className="text-xs text-muted-foreground">{status}</div>
      </div>
      <iframe
        ref={iframeRef}
        src={editorUrl}
        className="w-full min-h-[40rem] rounded-md border border-border bg-white"
        title="Self-hosted draw.io editor"
      />
    </div>
  )
}

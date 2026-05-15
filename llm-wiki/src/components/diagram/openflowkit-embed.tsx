'use client'

import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'

import type { FlowDocument } from '@/lib/types'

export type OpenFlowKitEmbedHandle = {
  requestSave: () => Promise<FlowDocument>
}

type PendingSave = {
  resolve: (document: FlowDocument) => void
  reject: (error: Error) => void
}

type OpenFlowKitEmbedProps = {
  diagramId: string
  title: string
  objective?: string
  owner?: string
  document: FlowDocument
  onDocumentSaved?: (document: FlowDocument) => void
  onStatusChange?: (status: string) => void
}

export const OPENFLOWKIT_EMBED_URL = process.env.NEXT_PUBLIC_OPENFLOWKIT_URL ?? ''

function makeRequestId() {
  return `save-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function resolveTargetOrigin(src: string) {
  if (!src) return '*'
  try {
    return new URL(src, window.location.origin).origin
  } catch {
    return '*'
  }
}

export const OpenFlowKitEmbed = forwardRef<OpenFlowKitEmbedHandle, OpenFlowKitEmbedProps>(function OpenFlowKitEmbed(
  { diagramId, title, objective = '', owner = '', document, onDocumentSaved, onStatusChange },
  ref,
) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const pendingSaves = useRef(new Map<string, PendingSave>())
  const [isReady, setIsReady] = useState(false)
  const sourceUrl = OPENFLOWKIT_EMBED_URL || '/openflowkit/#/home'
  const targetOrigin = useMemo(() => {
    if (typeof window === 'undefined') return '*'
    return resolveTargetOrigin(sourceUrl)
  }, [sourceUrl])

  const postInit = useCallback(() => {
    const iframe = iframeRef.current
    if (!iframe?.contentWindow) return
    iframe.contentWindow.postMessage(
      {
        type: 'llmwiki:openflowkit:init',
        diagramId,
        title,
        objective,
        owner,
        document,
      },
      targetOrigin,
    )
    onStatusChange?.('OpenFlowKit document sent')
  }, [diagramId, document, objective, onStatusChange, owner, targetOrigin, title])

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (targetOrigin !== '*' && event.origin !== targetOrigin) return
      const payload = event.data as { type?: string; requestId?: string; document?: FlowDocument; message?: string }
      if (!payload || typeof payload !== 'object') return
      if (payload.type === 'openflowkit:ready') {
        setIsReady(true)
        onStatusChange?.('OpenFlowKit ready')
        postInit()
        return
      }
      if (payload.type === 'openflowkit:document-loaded') {
        setIsReady(true)
        onStatusChange?.('OpenFlowKit document loaded')
        return
      }
      if (payload.type === 'openflowkit:document-saved' && payload.requestId && payload.document) {
        const pending = pendingSaves.current.get(payload.requestId)
        pendingSaves.current.delete(payload.requestId)
        onDocumentSaved?.(payload.document)
        pending?.resolve(payload.document)
        onStatusChange?.('OpenFlowKit document returned')
        return
      }
      if (payload.type === 'openflowkit:save-error' && payload.requestId) {
        const pending = pendingSaves.current.get(payload.requestId)
        pendingSaves.current.delete(payload.requestId)
        pending?.reject(new Error(payload.message || 'OpenFlowKit save failed'))
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [onDocumentSaved, onStatusChange, postInit, targetOrigin])

  useEffect(() => {
    if (isReady) postInit()
  }, [isReady, postInit])

  useImperativeHandle(ref, () => ({
    requestSave() {
      const iframe = iframeRef.current
      if (!iframe?.contentWindow) {
        return Promise.reject(new Error('OpenFlowKit iframe is not ready.'))
      }
      const requestId = makeRequestId()
      const promise = new Promise<FlowDocument>((resolve, reject) => {
        pendingSaves.current.set(requestId, { resolve, reject })
        window.setTimeout(() => {
          const pending = pendingSaves.current.get(requestId)
          if (!pending) return
          pendingSaves.current.delete(requestId)
          pending.reject(new Error('OpenFlowKit save timed out.'))
        }, 10000)
      })
      iframe.contentWindow.postMessage({ type: 'llmwiki:openflowkit:request-save', requestId }, targetOrigin)
      onStatusChange?.('Requesting OpenFlowKit document')
      return promise
    },
  }), [onStatusChange, targetOrigin])

  return (
    <iframe
      ref={iframeRef}
      src={sourceUrl}
      title="OpenFlowKit editor"
      onLoad={postInit}
      className="h-full min-h-[34rem] w-full border-0 bg-background"
      allow="clipboard-read; clipboard-write; fullscreen; downloads"
    />
  )
})

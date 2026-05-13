export type PageHeadingBlock = {
  id: string
  type: 'heading'
  level: number
  text: string
}

export type PageParagraphBlock = {
  id: string
  type: 'paragraph' | 'quote'
  text: string
}

export type PageBulletListBlock = {
  id: string
  type: 'bullet_list'
  items: string[]
}

export type PageTodoItem = {
  text: string
  checked: boolean
}

export type PageTodoListBlock = {
  id: string
  type: 'todo_list'
  items: PageTodoItem[]
}

export type PageImageBlock = {
  id: string
  type: 'image'
  url: string
  caption?: string
  alt?: string
  assetId?: string | null
}

export type PageBlock =
  | PageHeadingBlock
  | PageParagraphBlock
  | PageBulletListBlock
  | PageTodoListBlock
  | PageImageBlock

const IMAGE_RE = /^!\[([^\]]*)\]\(([^)]+)\)\s*$/
const HEADING_RE = /^(#{1,6})\s+(.+?)\s*$/
const TODO_RE = /^\s*[-*]\s+\[([xX ])\]\s+(.+?)\s*$/
const BULLET_RE = /^\s*[-*+]\s+(.+?)\s*$/

function blockId() {
  return `blk-${Math.random().toString(36).slice(2, 10)}`
}

export function createParagraphBlock(text = ''): PageParagraphBlock {
  return { id: blockId(), type: 'paragraph', text }
}

export function createHeadingBlock(text = 'Untitled section', level = 2): PageHeadingBlock {
  return { id: blockId(), type: 'heading', level, text }
}

export function createImageBlock(url: string, caption = '', assetId?: string | null): PageImageBlock {
  return { id: blockId(), type: 'image', url, caption, alt: caption, assetId }
}

export function normalizePageBlocks(input?: unknown): PageBlock[] {
  if (!Array.isArray(input) || input.length === 0) return [createParagraphBlock('')]
  const blocks = input.flatMap<PageBlock>((raw) => {
    if (!raw || typeof raw !== 'object') return []
    const block = raw as Record<string, unknown>
    const type = String(block.type || 'paragraph')
    const id = String(block.id || blockId())
    if (type === 'heading') {
      return [{ id, type: 'heading', level: Math.min(Math.max(Number(block.level || 1), 1), 6), text: String(block.text || '') }]
    }
    if (type === 'image') {
      const url = String(block.url || '')
      if (!url) return []
      return [{ id, type: 'image', url, caption: String(block.caption || ''), alt: String(block.alt || block.caption || ''), assetId: block.assetId ? String(block.assetId) : null }]
    }
    if (type === 'bullet_list') {
      const items = Array.isArray(block.items) ? block.items.map(item => String(item).trim()) : ['']
      return [{ id, type: 'bullet_list', items: items.length ? items : [''] }]
    }
    if (type === 'todo_list') {
      const items = Array.isArray(block.items)
        ? block.items.map((item) => {
            const record = item as Record<string, unknown>
            return { text: String(record?.text || ''), checked: Boolean(record?.checked) }
          })
        : [{ text: '', checked: false }]
      return [{ id, type: 'todo_list', items: items.length ? items : [{ text: '', checked: false }] }]
    }
    if (type === 'quote') {
      return [{ id, type: 'quote', text: String(block.text || '') }]
    }
    return [{ id, type: 'paragraph', text: String(block.text || '') }]
  })
  return blocks.length ? blocks : [createParagraphBlock('')]
}

export function markdownToPageBlocks(markdown?: string): PageBlock[] {
  const content = (markdown || '').trim()
  if (!content) return [createParagraphBlock('')]

  const blocks: PageBlock[] = []
  let paragraphLines: string[] = []
  let bulletItems: string[] = []
  let todoItems: PageTodoItem[] = []
  let quoteLines: string[] = []

  const flushParagraph = () => {
    if (paragraphLines.length) {
      blocks.push(createParagraphBlock(paragraphLines.join('\n')))
      paragraphLines = []
    }
  }
  const flushBullets = () => {
    if (bulletItems.length) {
      blocks.push({ id: blockId(), type: 'bullet_list', items: [...bulletItems] })
      bulletItems = []
    }
  }
  const flushTodos = () => {
    if (todoItems.length) {
      blocks.push({ id: blockId(), type: 'todo_list', items: [...todoItems] })
      todoItems = []
    }
  }
  const flushQuotes = () => {
    if (quoteLines.length) {
      blocks.push({ id: blockId(), type: 'quote', text: quoteLines.join('\n') })
      quoteLines = []
    }
  }
  const flushAll = () => {
    flushParagraph()
    flushBullets()
    flushTodos()
    flushQuotes()
  }

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trimEnd()
    const trimmed = line.trim()
    if (!trimmed) {
      flushAll()
      continue
    }
    const imageMatch = trimmed.match(IMAGE_RE)
    if (imageMatch) {
      flushAll()
      blocks.push(createImageBlock(imageMatch[2], imageMatch[1]))
      continue
    }
    const headingMatch = trimmed.match(HEADING_RE)
    if (headingMatch) {
      flushAll()
      blocks.push(createHeadingBlock(headingMatch[2], headingMatch[1].length))
      continue
    }
    const todoMatch = trimmed.match(TODO_RE)
    if (todoMatch) {
      flushParagraph()
      flushBullets()
      flushQuotes()
      todoItems.push({ text: todoMatch[2], checked: todoMatch[1].toLowerCase() === 'x' })
      continue
    }
    const bulletMatch = trimmed.match(BULLET_RE)
    if (bulletMatch) {
      flushParagraph()
      flushTodos()
      flushQuotes()
      bulletItems.push(bulletMatch[1])
      continue
    }
    if (trimmed.startsWith('>')) {
      flushParagraph()
      flushBullets()
      flushTodos()
      quoteLines.push(trimmed.replace(/^>\s?/, ''))
      continue
    }
    flushBullets()
    flushTodos()
    flushQuotes()
    paragraphLines.push(line)
  }

  flushAll()
  return blocks.length ? blocks : [createParagraphBlock('')]
}

export function pageBlocksToMarkdown(blocks: PageBlock[]): string {
  const normalized = normalizePageBlocks(blocks)
  const lines: string[] = []
  normalized.forEach((block) => {
    if (block.type === 'heading') {
      lines.push(`${'#'.repeat(block.level)} ${block.text}`.trimEnd())
    } else if (block.type === 'image') {
      lines.push(`![${(block.caption || block.alt || 'image').trim()}](${block.url})`)
    } else if (block.type === 'bullet_list') {
      block.items.forEach(item => lines.push(`- ${item}`.trimEnd()))
    } else if (block.type === 'todo_list') {
      block.items.forEach(item => lines.push(`- [${item.checked ? 'x' : ' '}] ${item.text}`.trimEnd()))
    } else if (block.type === 'quote') {
      block.text.split('\n').forEach(line => lines.push(`> ${line}`.trimEnd()))
    } else {
      lines.push(block.text.trimEnd())
    }
    lines.push('')
  })
  return lines.join('\n').trim()
}

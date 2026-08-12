import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Json Input'

function getWidget(node, name) {
  return node?.widgets?.find((w) => w.name === name)
}

function isConvertEnabled(node) {
  const widget = getWidget(node, 'convert_escaped_chars')
  return widget ? !!widget.value : false
}

// Escapes literal newline/tab/carriage-return characters found inside JSON
// string literals into \n / \t sequences, leaving structural whitespace
// between tokens untouched. Used before JSON.parse / JSON.stringify and
// mirrors the Python-side transform applied on output.
function escapeControlCharsInStrings(text) {
  let result = ''
  let inString = false
  let escaped = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (inString) {
      if (escaped) {
        result += ch
        escaped = false
      } else if (ch === '\\') {
        result += ch
        escaped = true
      } else if (ch === '"') {
        result += ch
        inString = false
      } else if (ch === '\n') {
        result += '\\n'
      } else if (ch === '\t') {
        result += '\\t'
      } else if (ch === '\r') {
        // Normalize CRLF and lone CR line breaks to \n so output is portable
        // across platforms regardless of how the text was typed/pasted.
        if (text[i + 1] !== '\n') {
          result += '\\n'
        }
        // else: swallow the \r; the following \n is escaped next iteration.
      } else {
        result += ch
      }
    } else {
      if (ch === '"') inString = true
      result += ch
    }
  }
  return result
}

// Inverse of escapeControlCharsInStrings: turns \n / \t / \r escape
// sequences inside JSON string literals into real newline/tab characters so
// multi-line strings preview nicely in the textarea. Other escape sequences
// (\", \\, \uXXXX, ...) are left untouched.
function unescapeControlCharsInStrings(text) {
  let result = ''
  let inString = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (inString) {
      if (ch === '\\' && i + 1 < text.length) {
        const next = text[i + 1]
        if (next === 'n') {
          result += '\n'
          i += 1
          continue
        }
        if (next === 't') {
          result += '\t'
          i += 1
          continue
        }
        if (next === 'r') {
          // Collapse \r or \r\n escapes into a single newline for display.
          if (text[i + 2] === '\\' && text[i + 3] === 'n') {
            result += '\n'
            i += 3
            continue
          }
          result += '\n'
          i += 1
          continue
        }
        result += ch + next
        i += 1
        continue
      } else if (ch === '"') {
        inString = false
        result += ch
      } else {
        result += ch
      }
    } else {
      if (ch === '"') inString = true
      result += ch
    }
  }
  return result
}

function applyValidState(textarea, errorEl) {
  textarea.style.removeProperty('border')
  textarea.style.removeProperty('outline')
  errorEl.textContent = ''
  errorEl.style.display = 'none'
}

function applyInvalidState(textarea, errorEl, message) {
  textarea.style.border = '1px solid #e33'
  textarea.style.outline = 'none'
  errorEl.textContent = message
  errorEl.style.display = 'block'
}

function validateJson(node, textarea, errorEl) {
  const raw = textarea.value
  if (raw.trim() === '') {
    applyValidState(textarea, errorEl)
    return
  }
  const value = isConvertEnabled(node) ? escapeControlCharsInStrings(raw) : raw
  try {
    JSON.parse(value)
    applyValidState(textarea, errorEl)
  } catch (e) {
    applyInvalidState(textarea, errorEl, e.message)
  }
}

function attachJsonValidation(node) {
  if (node._tinybeeJsonInputAttached) return
  const widget = getWidget(node, 'json')
  const textarea = widget?.inputEl
  if (!textarea) return

  // Anchor the error banner to the textarea's own wrapper (not the node) so it
  // overlays the bottom of the textarea instead of pushing/spilling into other
  // widgets or past the node's edge.
  const container = textarea.parentElement ?? textarea
  if (container !== textarea && getComputedStyle(container).position === 'static') {
    container.style.position = 'relative'
  }

  const errorEl = document.createElement('div')
  errorEl.className = 'tinybee-json-input-error'
  errorEl.style.cssText =
    'display:none;position:absolute;left:0;right:0;bottom:0;max-height:50%;overflow:auto;' +
    'box-sizing:border-box;color:#fff;background:rgba(221,51,51,0.85);font-size:11px;' +
    'padding:2px 4px;white-space:pre-wrap;word-break:break-word;pointer-events:none;z-index:5;'
  container.appendChild(errorEl)

  const handler = () => validateJson(node, textarea, errorEl)
  textarea.addEventListener('input', handler)

  node._tinybeeJsonInputAttached = true

  // Validate current value (covers workflow load / node clone)
  handler()
}

function formatJson(node) {
  const widget = getWidget(node, 'json')
  const textarea = widget?.inputEl
  if (!textarea) return

  const convert = isConvertEnabled(node)
  try {
    const source = convert ? escapeControlCharsInStrings(textarea.value) : textarea.value
    const parsed = JSON.parse(source)
    let formatted = JSON.stringify(parsed, null, 2)
    if (convert) formatted = unescapeControlCharsInStrings(formatted)
    textarea.value = formatted
    textarea.dispatchEvent(new Event('input', { bubbles: true }))
    app.canvas?.setDirty(true, true)
  } catch (e) {
    // Invalid JSON — leave the text untouched; the existing validator already surfaces the error
  }
}

function addFormatButton(node) {
  if (node._tinybeeJsonFormatButtonAdded) return
  node.addWidget('button', 'Format Json', null, () => formatJson(node), { serialize: false })
  node._tinybeeJsonFormatButtonAdded = true
}

// Gives the auto-generated "convert_escaped_chars" boolean widget a friendly
// label and, when toggled, converts the current textarea content between its
// "raw \n / \t escapes" and "real newline / tab characters" representations
// so the displayed text always matches the new mode.
function attachConvertToggle(node) {
  if (node._tinybeeJsonConvertToggleAttached) return
  const widget = getWidget(node, 'convert_escaped_chars')
  if (!widget) return

  widget.label = 'Convert Escaped Chars'

  const originalCallback = widget.callback
  widget.callback = function (value, ...rest) {
    const result = originalCallback ? originalCallback.call(this, value, ...rest) : undefined

    const jsonWidget = getWidget(node, 'json')
    const textarea = jsonWidget?.inputEl
    if (textarea) {
      textarea.value = value
        ? unescapeControlCharsInStrings(textarea.value)
        : escapeControlCharsInStrings(textarea.value)
      textarea.dispatchEvent(new Event('input', { bubbles: true }))
    }
    app.canvas?.setDirty(true, true)

    return result
  }

  node._tinybeeJsonConvertToggleAttached = true
}

app.registerExtension({
  name: 'TinyBee.JsonInput',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addFormatButton(this)
      attachConvertToggle(this)
      requestAnimationFrame(() => attachJsonValidation(this))
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addFormatButton(this)
      attachConvertToggle(this)
      requestAnimationFrame(() => attachJsonValidation(this))
      return result
    }
  },
})

import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Json Input'

function getWidget(node, name) {
  return node?.widgets?.find((w) => w.name === name)
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

function validateJson(textarea, errorEl) {
  const value = textarea.value
  if (value.trim() === '') {
    applyValidState(textarea, errorEl)
    return
  }
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

  const handler = () => validateJson(textarea, errorEl)
  textarea.addEventListener('input', handler)

  node._tinybeeJsonInputAttached = true

  // Validate current value (covers workflow load / node clone)
  handler()
}

function formatJson(node) {
  const widget = getWidget(node, 'json')
  const textarea = widget?.inputEl
  if (!textarea) return

  try {
    const formatted = JSON.stringify(JSON.parse(textarea.value), null, 2)
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

app.registerExtension({
  name: 'TinyBee.JsonInput',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addFormatButton(this)
      requestAnimationFrame(() => attachJsonValidation(this))
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addFormatButton(this)
      requestAnimationFrame(() => attachJsonValidation(this))
      return result
    }
  },
})

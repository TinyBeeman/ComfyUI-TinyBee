import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Token Replace'
const MAX_TOKENS = 10

function clampCount(value) {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  if (Number.isNaN(numeric)) return 1
  return Math.max(1, Math.min(MAX_TOKENS, numeric))
}

function getWidget(node, name) {
  return node?.widgets?.find((w) => w.name === name)
}

function isTokenInput(input) {
  return /^input_[1-9]$/.test(String(input?.name ?? ''))
}

function syncTokenSlots(node) {
  if (!node) return

  const countWidget = getWidget(node, 'token_count')
  const count = clampCount(countWidget?.value)
  if (countWidget) countWidget.value = count

  // Remove token inputs whose index >= count (backwards so indices stay valid)
  for (let i = (node.inputs?.length ?? 0) - 1; i >= 0; i--) {
    const input = node.inputs[i]
    if (!isTokenInput(input)) continue
    const index = Number.parseInt(input.name.replace('input_', ''), 10)
    if (index >= count) {
      if ((input?.link ?? null) !== null) {
        node._tinybeeTokenTrimBlocked = true
      } else {
        node.removeInput(i)
      }
    }
  }

  // Add any missing inputs for indices 1 through count-1
  const existing = new Set(
    (node.inputs ?? []).filter(isTokenInput).map((inp) => inp.name)
  )
  for (let i = 1; i < count; i++) {
    if (!existing.has(`input_${i}`)) {
      node.addInput(`input_${i}`, 'STRING')
    }
  }

  node.setSize?.(node.computeSize())
  app.canvas?.setDirty(true, true)
}

function addRefreshButton(node) {
  if (node._tinybeeTokenReplaceButtonAdded) return
  node.addWidget('button', 'Refresh Inputs', null, () => syncTokenSlots(node), { serialize: false })
  node._tinybeeTokenReplaceButtonAdded = true
}

app.registerExtension({
  name: 'TinyBee.TokenReplace',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const self = this
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addRefreshButton(this)
      // Defer so ComfyUI finishes adding all optional inputs to node.inputs first
      requestAnimationFrame(() => syncTokenSlots(self))
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addRefreshButton(this)
      syncTokenSlots(this)
      return result
    }

    const onConnectionsChange = nodeType.prototype.onConnectionsChange
    nodeType.prototype.onConnectionsChange = function () {
      const result = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined
      this._tinybeeTokenTrimBlocked = false
      return result
    }
  },
})

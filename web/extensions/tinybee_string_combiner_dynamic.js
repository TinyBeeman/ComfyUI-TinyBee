import { app } from '../../../scripts/app.js'

const NODE_NAME = 'String Combiner'
const MAX_LISTS = 10

function clampCount(value) {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  if (Number.isNaN(numeric)) return 1
  return Math.max(1, Math.min(MAX_LISTS, numeric))
}

function getWidget(node, name) {
  return node?.widgets?.find((w) => w?.name === name)
}

function isListInput(input) {
  return /^list_\d+$/.test(String(input?.name ?? ''))
}

function syncInputs(node) {
  if (!node) return

  const countWidget = getWidget(node, 'num_lists')
  const count = clampCount(countWidget?.value)

  if (countWidget) countWidget.value = count

  const wanted = new Set()
  for (let i = 1; i <= count; i += 1) {
    wanted.add(`list_${i}`)
  }

  for (let i = node.inputs.length - 1; i >= 0; i -= 1) {
    const input = node.inputs[i]
    if (!isListInput(input)) continue
    if (wanted.has(input.name)) continue

    if ((input?.link ?? null) !== null) {
      node._tinybeeCombinerTrimBlocked = true
      continue
    }

    node.removeInput(i)
  }

  const existing = new Set(node.inputs.filter(isListInput).map((inp) => inp.name))
  for (let i = 1; i <= count; i += 1) {
    const name = `list_${i}`
    if (!existing.has(name)) {
      node.addInput(name, 'STRING')
    }
  }

  node.setSize?.(node.computeSize())
  app.canvas?.setDirty(true, true)
}

function addRefreshButton(node) {
  if (node._tinybeeCombinerButtonAdded) return
  node.addWidget('button', 'Refresh Inputs', null, () => syncInputs(node), { serialize: false })
  node._tinybeeCombinerButtonAdded = true
}

app.registerExtension({
  name: 'TinyBee.StringCombinerDynamic',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addRefreshButton(this)
      syncInputs(this)
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addRefreshButton(this)
      syncInputs(this)
      return result
    }

    const onConnectionsChange = nodeType.prototype.onConnectionsChange
    nodeType.prototype.onConnectionsChange = function () {
      const result = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined
      this._tinybeeCombinerTrimBlocked = false
      return result
    }
  },
})

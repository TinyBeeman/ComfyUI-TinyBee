import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Encode Any Properties (Dynamic)'
const MAX_PROPS = 16

function clampCount(value) {
  const n = Number.parseInt(String(value ?? ''), 10)
  return Number.isNaN(n) ? 1 : Math.max(1, Math.min(MAX_PROPS, n))
}

function getCountWidget(node) {
  return node.widgets?.find((w) => w.name === 'num_properties')
}

function getCurrentSlotCount(node) {
  let max = 0
  for (let i = 1; i <= MAX_PROPS; i++) {
    if (node.inputs?.some((inp) => inp.name === `value_${i}`)) max = i
  }
  return max
}

function syncSlots(node, targetCount) {
  if (!node) return
  const desired = clampCount(targetCount)

  // Show / hide name_N widgets (always kept in node.widgets for serialization)
  for (let i = 1; i <= MAX_PROPS; i++) {
    const nameWidget = node.widgets?.find((w) => w.name === `name_${i}`)
    if (nameWidget) nameWidget.hidden = i > desired
  }

  // Add / remove value_N connection slots
  const current = getCurrentSlotCount(node)

  for (let i = current; i > desired; i--) {
    const idx = node.inputs?.findIndex((inp) => inp.name === `value_${i}`) ?? -1
    if (idx >= 0 && !node.inputs[idx].link) {
      node.removeInput(idx)
    }
  }

  for (let i = current + 1; i <= desired; i++) {
    node.addInput(`value_${i}`, '*')
  }

  node.setSize?.(node.computeSize())
  app.canvas?.setDirty(true, true)
}

function addRefreshButton(node) {
  if (node._tinybeePropsRefreshAdded) return
  node.addWidget('button', 'Refresh', null, () => {
    const countWidget = getCountWidget(node)
    syncSlots(node, countWidget?.value)
  }, { serialize: false })
  node._tinybeePropsRefreshAdded = true
}

app.registerExtension({
  name: 'TinyBee.EncodeAnyPropertiesDynamic',

  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addRefreshButton(this)
      const countWidget = getCountWidget(this)
      syncSlots(this, countWidget?.value)
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addRefreshButton(this)
      // Widget values (including num_properties and all name_N) are already
      // restored from the workflow before onConfigure fires, so this is correct.
      const countWidget = getCountWidget(this)
      syncSlots(this, countWidget?.value)
      return result
    }
  },
})

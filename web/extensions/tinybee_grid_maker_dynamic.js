import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Grid Maker (Dynamic)'
const MAX_DIM = 10

function clampDim(value) {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  if (Number.isNaN(numeric)) {
    return 1
  }
  return Math.max(1, Math.min(MAX_DIM, numeric))
}

function getWidget(node, name) {
  return node?.widgets?.find((widget) => widget?.name === name)
}

function isGridCellInput(input) {
  return /^img_\d+_\d+$/.test(String(input?.name ?? ''))
}

function desiredCellNames(rows, cols) {
  const names = new Set()
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      names.add(`img_${r}_${c}`)
    }
  }
  return names
}

function syncGridInputs(node) {
  if (!node) {
    return
  }

  const rowsWidget = getWidget(node, 'rows')
  const colsWidget = getWidget(node, 'cols')

  const rows = clampDim(rowsWidget?.value)
  const cols = clampDim(colsWidget?.value)

  if (rowsWidget) {
    rowsWidget.value = rows
  }
  if (colsWidget) {
    colsWidget.value = cols
  }

  const wanted = desiredCellNames(rows, cols)

  for (let i = node.inputs.length - 1; i >= 0; i -= 1) {
    const input = node.inputs[i]
    if (!isGridCellInput(input)) {
      continue
    }
    if (wanted.has(input.name)) {
      continue
    }

    if ((input?.link ?? null) !== null) {
      node._tinybeeGridTrimBlocked = true
      continue
    }

    node.removeInput(i)
  }

  const existing = new Set(node.inputs.filter(isGridCellInput).map((input) => input.name))
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const inputName = `img_${r}_${c}`
      if (!existing.has(inputName)) {
        node.addInput(inputName, 'IMAGE')
      }
    }
  }

  node.setSize?.(node.computeSize())
  app.canvas?.setDirty(true, true)
}

function addRefreshButton(node) {
  if (node._tinybeeGridMakerButtonAdded) {
    return
  }

  node.addWidget('button', 'Refresh Inputs', null, () => syncGridInputs(node), { serialize: false })
  node._tinybeeGridMakerButtonAdded = true
}

app.registerExtension({
  name: 'TinyBee.GridMakerDynamic',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) {
      return
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addRefreshButton(this)
      syncGridInputs(this)
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addRefreshButton(this)
      syncGridInputs(this)
      return result
    }

    const onConnectionsChange = nodeType.prototype.onConnectionsChange
    nodeType.prototype.onConnectionsChange = function () {
      const result = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined
      this._tinybeeGridTrimBlocked = false
      return result
    }
  },
})

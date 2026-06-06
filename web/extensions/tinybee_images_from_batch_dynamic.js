import { app } from '../../../scripts/app.js'

const NODE_NAME = 'Images From Batch'
const MAX_OUTPUTS = 32

function clampCount(value) {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  if (Number.isNaN(numeric)) {
    return 1
  }
  return Math.max(1, Math.min(MAX_OUTPUTS, numeric))
}

function getImgCountWidget(node) {
  return node?.widgets?.find((widget) => widget?.name === 'imgCount')
}

function syncImageOutputs(node, targetCount) {
  if (!node) {
    return
  }

  const desiredCount = clampCount(targetCount)

  while (node.outputs.length > desiredCount) {
    const lastOutput = node.outputs[node.outputs.length - 1]
    if ((lastOutput?.links?.length ?? 0) > 0) {
      node._tinybeeTrimBlocked = true
      break
    }
    node.removeOutput(node.outputs.length - 1)
  }

  while (node.outputs.length < desiredCount) {
    const nextIndex = node.outputs.length
    node.addOutput(`img${nextIndex}`, 'IMAGE')
  }

  for (let index = 0; index < node.outputs.length; index += 1) {
    const output = node.outputs[index]
    if (!output) {
      continue
    }
    output.name = `img${index}`
    output.type = 'IMAGE'
  }

  node.setSize?.(node.computeSize())
  app.canvas?.setDirty(true, true)
}

function addUpdateButton(node) {
  if (node._tinybeeImgBatchButtonAdded) {
    return
  }

  const onUpdateOutputs = () => {
    const countWidget = getImgCountWidget(node)
    const count = clampCount(countWidget?.value)
    if (countWidget) {
      countWidget.value = count
    }
    syncImageOutputs(node, count)
  }

  node.addWidget('button', 'Update Outputs', null, onUpdateOutputs, { serialize: false })
  node._tinybeeImgBatchButtonAdded = true
}

app.registerExtension({
  name: 'TinyBee.ImagesFromBatchDynamic',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) {
      return
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      addUpdateButton(this)
      const countWidget = getImgCountWidget(this)
      syncImageOutputs(this, countWidget?.value)
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      addUpdateButton(this)
      const countWidget = getImgCountWidget(this)
      syncImageOutputs(this, countWidget?.value)
      return result
    }

    const onConnectionsChange = nodeType.prototype.onConnectionsChange
    nodeType.prototype.onConnectionsChange = function () {
      const result = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined
      this._tinybeeTrimBlocked = false
      return result
    }
  },
})

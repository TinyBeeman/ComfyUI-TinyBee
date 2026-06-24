import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

const NODE_NAME = 'Save Image w/Meta'

function buildViewUrl(img) {
  const params = new URLSearchParams({
    filename: img.filename,
    subfolder: img.subfolder || '',
    type: img.type || 'output',
  })
  return api.apiURL(`/view?${params}`)
}

function applyImagePreview(node, images) {
  const imgs = []
  let pending = images.length
  for (const img of images) {
    const el = new Image()
    el.onload = () => {
      if (--pending === 0) app.graph?.setDirtyCanvas(true, true)
    }
    el.src = buildViewUrl(img)
    imgs.push(el)
  }
  node.imgs = imgs
  node.imageIndex = null
  app.graph?.setDirtyCanvas(true, true)
}

app.registerExtension({
  name: 'TinyBee.SaveImageWithMetaPreview',

  async beforeConfigureGraph() {
    const originalOnExecuted = app.canvas.onExecuted
    app.canvas.onExecuted = function (message) {
      originalOnExecuted?.call(this, message)

      const images = message?.output?.images
      if (!images?.length) return

      const nodeId = String(message.node ?? '')

      if (!nodeId.includes(':')) {
        // Top-level: plain node ID, find and apply directly
        const node = app.graph?.getNodeById(parseInt(nodeId, 10))
        if (node && (node.type === NODE_NAME || node.comfyClass === NODE_NAME)) {
          applyImagePreview(node, images)
        }
        return
      }

      // Subgraph: compound ID like "3:7" means subgraph boundary 3, inner node 7.
      // Multi-level nesting ("1:3:7") is also handled by traversing each segment.
      const parts = nodeId.split(':')
      const leafId = parseInt(parts[parts.length - 1], 10)

      let currentGraph = app.graph
      for (let i = 0; i < parts.length - 1; i++) {
        const instance = currentGraph?.getNodeById(parseInt(parts[i], 10))
        if (!instance?.subgraph) { currentGraph = null; break }
        currentGraph = instance.subgraph
      }
      const innerNode = currentGraph?.getNodeById(leafId)

      if (innerNode && (innerNode.type === NODE_NAME || innerNode.comfyClass === NODE_NAME)) {
        // Apply to inner node so the preview is visible when viewing inside the subgraph
        applyImagePreview(innerNode, images)

        // Apply to boundary node so the preview is visible from outside the subgraph
        const displayId = parseInt(String(message.display_node ?? parts[0]), 10)
        const boundaryNode = app.graph?.getNodeById(displayId)
        if (boundaryNode) applyImagePreview(boundaryNode, images)
      }
    }
  },

  nodeCreated(node) {
    if (node.comfyClass !== NODE_NAME && node.type !== NODE_NAME) return
    node.isVirtualNode = false
  },
})

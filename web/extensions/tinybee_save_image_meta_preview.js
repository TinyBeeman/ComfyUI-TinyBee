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

// Returns the Y coordinate of the bottom edge of all visible widgets.
// onDrawBackground is called before drawNodeWidgets, so widget.y values come
// from the previous frame's layout pass. On the very first frame we fall back
// to estimating from the widget count.
function getWidgetsBottom(node) {
  const startY = node.widgets_start_y ?? LiteGraph.NODE_TITLE_HEIGHT ?? 30

  if (!node.widgets || node.widgets.length === 0) return startY

  let maxBottom = startY
  let anyHadY = false

  for (const w of node.widgets) {
    if (w.hidden) continue
    if (w.y != null) {
      anyHadY = true
      const h = w.computedHeight ?? LiteGraph.NODE_WIDGET_HEIGHT ?? 20
      maxBottom = Math.max(maxBottom, w.y + h)
    }
  }

  if (!anyHadY) {
    // First-frame fallback: estimate from widget count
    const widgetH = (LiteGraph.NODE_WIDGET_HEIGHT ?? 20) + 4
    maxBottom = startY + node.widgets.length * widgetH
  }

  return maxBottom
}

app.registerExtension({
  name: 'TinyBee.SaveImageWithMetaPreview',

  async beforeConfigureGraph() {
    const nodeType = LiteGraph.registered_node_types[NODE_NAME]

    if (nodeType) {
      nodeType.prototype.getCanvasMenuOptions = function (options) {
        this.isVirtualNode = false
      }

      nodeType.prototype.onExecuted = function (message) {
        const images = message?.images
        if (!images?.length) return

        this.imgs = images.map((img) => {
          const el = new Image()
          el.src = buildViewUrl(img)
          el.onload = () => app.graph?.setDirtyCanvas(true, true)
          return el
        })

        this.imageIndex = 0
        app.graph?.setDirtyCanvas(true, true)
      }

      nodeType.prototype.onDrawBackground = function (ctx) {
        if (!this.imgs || this.imgs.length === 0) return

        const img = this.imgs[this.imageIndex || 0]
        if (!img || !img.complete) return

        const margin = 10
        // Start the image below all visible widgets, not at the top of them
        const top_offset = getWidgetsBottom(this) + margin

        const max_w = this.size[0] - margin * 2
        const max_h = this.size[1] - top_offset - margin

        if (max_w <= 0 || max_h <= 0) return

        const imgRatio = img.width / img.height
        const targetRatio = max_w / max_h

        let draw_w = max_w
        let draw_h = max_h

        if (imgRatio > targetRatio) {
          draw_h = max_w / imgRatio
        } else {
          draw_w = max_h * imgRatio
        }

        const offset_x = margin + (max_w - draw_w) / 2
        const offset_y = top_offset + (max_h - draw_h) / 2

        ctx.save()
        ctx.drawImage(img, offset_x, offset_y, draw_w, draw_h)
        ctx.restore()
      }
    }
  },

  nodeCreated(node) {
    if (node.comfyClass !== NODE_NAME && node.type !== NODE_NAME) return
    node.isVirtualNode = false
    node.show_canvas_preview = true
  },
})

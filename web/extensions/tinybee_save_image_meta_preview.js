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

app.registerExtension({
  name: 'TinyBee.SaveImageWithMetaPreview',

  async beforeConfigureGraph() {
    const nodeType = LiteGraph.registered_node_types[NODE_NAME];
    
    if (nodeType) {
      // Ensure the engine serializes this node's visual layer
      nodeType.prototype.getCanvasMenuOptions = function(options) {
        // This forces ComfyUI to see this node as eligible for subgraph promotion
        this.isVirtualNode = false;
      };

      nodeType.prototype.onExecuted = function (message) {
        const images = message?.images;
        if (!images?.length) return;

        this.imgs = images.map(img => {
          const el = new Image();
          el.src = buildViewUrl(img);
          el.onload = () => app.graph?.setDirtyCanvas(true, true);
          return el;
        });

        this.imageIndex = 0;
        app.graph?.setDirtyCanvas(true, true);
      };

      // Proportional aspect-ratio fitting
      nodeType.prototype.onDrawBackground = function(ctx) {
        if (!this.imgs || this.imgs.length === 0) return;
        
        const img = this.imgs[this.imageIndex || 0];
        if (!img || !img.complete) return;
        
        const margin = 10;
        const top_offset = this.widgets_start_y || 60;
        
        // Max allowable bounds
        const max_w = this.size[0] - margin * 2;
        const max_h = this.size[1] - top_offset - margin;
        
        if (max_w <= 0 || max_h <= 0) return;

        // Calculate aspect ratios
        const imgRatio = img.width / img.height;
        const targetRatio = max_w / max_h;
        
        let draw_w = max_w;
        let draw_h = max_h;
        
        if (imgRatio > targetRatio) {
          // Image is wider than target area bounds
          draw_h = max_w / imgRatio;
        } else {
          // Image is taller than target area bounds
          draw_w = max_h * imgRatio;
        }
        
        // Center the image within the bounding box dynamically
        const offset_x = margin + (max_w - draw_w) / 2;
        const offset_y = top_offset + (max_h - draw_h) / 2;
        
        ctx.save();
        ctx.drawImage(img, offset_x, offset_y, draw_w, draw_h);
        ctx.restore();
      };
    }
  },

  nodeCreated(node) {
    if (node.comfyClass !== NODE_NAME && node.type !== NODE_NAME) return;
    node.isVirtualNode = false;
    // Tell the wrapper compilation model to look for visual data here
    node.show_canvas_preview = true; 
  }
});
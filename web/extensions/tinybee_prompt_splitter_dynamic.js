import { app } from '../../../scripts/app.js'

function parsePromptEntries(text) {
  const entries = []
  let currentPrompt = ''
  let currentNegs = []

  const finalizeEntry = () => {
    if (!currentPrompt) {
      return
    }
    entries.push({
      prompt: currentPrompt.trim(),
      neg: currentNegs.filter(Boolean).join(', '),
    })
    currentPrompt = ''
    currentNegs = []
  }

  for (const rawLine of String(text ?? '').split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line) {
      continue
    }
    if (line.toLowerCase().startsWith('neg:')) {
      if (currentPrompt) {
        const negText = line.slice(4).trim()
        if (negText) {
          currentNegs.push(negText)
        }
      }
      continue
    }
    finalizeEntry()
    currentPrompt = line
  }

  finalizeEntry()
  return entries
}

function ensureOutputPair(node, index) {
  while (node.outputs.length < index * 2) {
    const nextIndex = node.outputs.length / 2 + 1
    node.addOutput(`prompt${nextIndex}`, 'STRING')
    node.addOutput(`neg${nextIndex}`, 'STRING')
  }

  node.outputs[(index - 1) * 2].name = `prompt${index}`
  node.outputs[(index - 1) * 2 + 1].name = `neg${index}`
}

function syncPromptOutputs(node, targetCount) {
  const maxPairs = node._tinybeeMaxPairs ?? 32
  const desiredCount = Math.max(1, Math.min(maxPairs, targetCount))

  while (node.outputs.length > desiredCount * 2) {
    const lastPrompt = node.outputs[node.outputs.length - 2]
    const lastNeg = node.outputs[node.outputs.length - 1]
    if ((lastPrompt?.links?.length ?? 0) > 0 || (lastNeg?.links?.length ?? 0) > 0) {
      node._tinybeeTrimBlocked = true
      break
    }
    node.removeOutput(node.outputs.length - 1)
    node.removeOutput(node.outputs.length - 1)
  }

  for (let pairIndex = 1; pairIndex <= desiredCount; pairIndex += 1) {
    ensureOutputPair(node, pairIndex)
  }

  for (let pairIndex = 1; pairIndex <= Math.floor(node.outputs.length / 2); pairIndex += 1) {
    const promptSlot = node.outputs[(pairIndex - 1) * 2]
    const negSlot = node.outputs[(pairIndex - 1) * 2 + 1]
    if (promptSlot) {
      promptSlot.name = `prompt${pairIndex}`
      promptSlot.type = 'STRING'
    }
    if (negSlot) {
      negSlot.name = `neg${pairIndex}`
      negSlot.type = 'STRING'
    }
  }

  node.setSize?.(node.computeSize())
  app.canvas.setDirty(true)
}

function addResetButton(node) {
  if (node._tinybeeResetWidgetAdded) {
    return
  }

  const onResetPrompts = () => {
    const promptsWidget = node.widgets?.find((widget) => widget.name === 'prompts')
    const entries = parsePromptEntries(promptsWidget?.value ?? '')
    syncPromptOutputs(node, entries.length)
  }

  node.addWidget('button', 'Reset Prompts', null, onResetPrompts, { serialize: false })
  node._tinybeeResetWidgetAdded = true
}

app.registerExtension({
  name: 'TinyBee.PromptSplitterDynamic',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== 'Prompt Splitter (Dynamic)') {
      return
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined
      this._tinybeeMaxPairs = 32
      addResetButton(this)

      const promptsWidget = this.widgets?.find((widget) => widget.name === 'prompts')
      const initialEntries = parsePromptEntries(promptsWidget?.value ?? '')
      syncPromptOutputs(this, initialEntries.length)
      return result
    }

    const onConfigure = nodeType.prototype.onConfigure
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure ? onConfigure.apply(this, arguments) : undefined
      this._tinybeeMaxPairs = 32
      addResetButton(this)
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

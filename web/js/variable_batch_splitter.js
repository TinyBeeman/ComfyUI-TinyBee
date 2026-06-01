import { app } from '../../../scripts/app.js'

const EXTENSION_NAME = 'TinyBee.VariableBatchSplitter'
const SET_NODE_NAME = 'Set Vars From Batch'
const GET_NODE_NAME = 'Get Variable'
const REGISTRY_KEY = '__tinybeeVariableRegistry'
const LOADED_FLAG = '__tinybeeVariableBatchSplitterLoaded'

if (!globalThis[LOADED_FLAG]) {
  globalThis[LOADED_FLAG] = true

  function parseVariableNames(rawValue) {
    return String(rawValue ?? '')
      .split(/[^\w]+/)
      .map((name) => name.trim())
      .filter((name) => name.length > 0)
  }

  function hasWidget(node, widgetName) {
    return Boolean(getWidget(node, widgetName))
  }

  function isSetNode(node) {
    return (
      node?.comfyClass === SET_NODE_NAME ||
      node?.type === SET_NODE_NAME ||
      node?.title === SET_NODE_NAME ||
      hasWidget(node, 'variable_names')
    )
  }

  function isGetNode(node) {
    return (
      node?.comfyClass === GET_NODE_NAME ||
      node?.type === GET_NODE_NAME ||
      node?.title === GET_NODE_NAME ||
      hasWidget(node, 'variable_name')
    )
  }

  function getWidget(node, widgetName) {
    return node?.widgets?.find((widget) => widget?.name === widgetName)
  }

  function getRegistry() {
    if (!globalThis[REGISTRY_KEY]) {
      globalThis[REGISTRY_KEY] = {
        names: [],
        byNodeId: {},
      }
    }
    return globalThis[REGISTRY_KEY]
  }

  function collectVariableNamesFromGraph() {
    const graphNodes = app.graph?._nodes ?? []
    const allNames = []
    const byNodeId = {}

    for (const node of graphNodes) {
      if (!isSetNode(node)) {
        continue
      }
      const variableNamesWidget = getWidget(node, 'variable_names')
      const names = parseVariableNames(variableNamesWidget?.value)
      byNodeId[node.id] = names
      for (const name of names) {
        allNames.push(name)
      }
    }

    const uniqueNames = [...new Set(allNames)]
    uniqueNames.sort((a, b) => a.localeCompare(b))

    const registry = getRegistry()
    registry.names = uniqueNames
    registry.byNodeId = byNodeId

    globalThis.TinyBeeVariableNames = uniqueNames
    return uniqueNames
  }

  function updateGetNodeDropdown(node, names) {
    if (!isGetNode(node)) {
      return
    }

    const widget = getWidget(node, 'variable_name')
    if (!widget) {
      return
    }

    const valueList = names.length > 0 ? [...names] : ['']
    const selected = String(widget.value ?? '')

    widget.options = widget.options ?? {}
    widget.options.values = valueList

    if (!valueList.includes(selected)) {
      widget.value = valueList[0]
    }

    widget.callback?.call(widget, widget.value, node, widget)
  }

  function refreshVariableRegistryAndDropdowns() {
    const names = collectVariableNamesFromGraph()
    const graphNodes = app.graph?._nodes ?? []

    for (const node of graphNodes) {
      updateGetNodeDropdown(node, names)
    }

    app.canvas?.setDirty?.(true, true)
  }

  function hookSetNodeWidget(node) {
    const variableNamesWidget = getWidget(node, 'variable_names')
    if (!variableNamesWidget || variableNamesWidget._tinybeeHooked) {
      return
    }

    const originalCallback = variableNamesWidget.callback
    variableNamesWidget.callback = function () {
      const result = originalCallback ? originalCallback.apply(this, arguments) : undefined
      queueMicrotask(refreshVariableRegistryAndDropdowns)
      return result
    }

    variableNamesWidget._tinybeeHooked = true
  }

  app.registerExtension({
    name: EXTENSION_NAME,
    beforeRegisterNodeDef(nodeType, nodeData) {
      const isTargetNode = nodeData.name === SET_NODE_NAME || nodeData.name === GET_NODE_NAME
      if (!isTargetNode) {
        return
      }

      const onNodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined

        if (hasWidget(this, 'variable_names')) {
          hookSetNodeWidget(this)
        }

        queueMicrotask(refreshVariableRegistryAndDropdowns)
        return result
      }

      const onConfigure = nodeType.prototype.onConfigure
      nodeType.prototype.onConfigure = function () {
        const result = onConfigure ? onConfigure.apply(this, arguments) : undefined

        if (hasWidget(this, 'variable_names')) {
          hookSetNodeWidget(this)
        }

        queueMicrotask(refreshVariableRegistryAndDropdowns)
        return result
      }

      const onConnectionsChange = nodeType.prototype.onConnectionsChange
      nodeType.prototype.onConnectionsChange = function () {
        const result = onConnectionsChange ? onConnectionsChange.apply(this, arguments) : undefined
        queueMicrotask(refreshVariableRegistryAndDropdowns)
        return result
      }

      const onRemoved = nodeType.prototype.onRemoved
      nodeType.prototype.onRemoved = function () {
        const result = onRemoved ? onRemoved.apply(this, arguments) : undefined
        queueMicrotask(refreshVariableRegistryAndDropdowns)
        return result
      }

      const onDrawForeground = nodeType.prototype.onDrawForeground
      nodeType.prototype.onDrawForeground = function () {
        const result = onDrawForeground ? onDrawForeground.apply(this, arguments) : undefined
        if (hasWidget(this, 'variable_name')) {
          updateGetNodeDropdown(this, getRegistry().names)
        }
        return result
      }
    },
    setup() {
      refreshVariableRegistryAndDropdowns()
      setTimeout(refreshVariableRegistryAndDropdowns, 0)
    },
  })
}

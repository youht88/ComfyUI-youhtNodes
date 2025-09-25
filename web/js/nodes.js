import { app } from "/scripts/app.js";

app.registerExtension({
	name: "youhtNodes.jsnodes",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if(!nodeData?.category?.startsWith("youht")) {
			return;
		}
		switch (nodeData.name) {
			case "pyScript":
				const originalOnNodeCreated = nodeType.prototype.onNodeCreated || function() {};
				nodeType.prototype.onNodeCreated = function () {
					originalOnNodeCreated.apply(this, arguments);
			
					this._type = "*";
                    this.addWidget("button","删除参数",null,()=>{
                        if (this.inputs.length<=1){
                            return
                        }
                        const to_remove_value = this.widgets.find(widget => widget.name === "arg_name")["value"]
                        if (["a","b","c","d","script","arg_name"].includes(to_remove_value)) return;
                        const to_remove_index  = this.inputs.findIndex(input => input.name === to_remove_value);
                        
                        if (to_remove_index !== -1){
                            this.removeInput(to_remove_index);
                        }
                    })
					this.addWidget("button", "新增参数", null, () => {
						if (!this.inputs) {
							this.inputs = [];
						}
                        const to_add_value = this.widgets.find(widget => widget.name === "arg_name")["value"]
                        if (["a","b","c","d","script","arg_name"].includes(to_add_value)) return;
                        const to_add_index  = this.inputs.findIndex(input => input.name === to_add_value);
                        if (to_add_index!=-1) return; // already set, do nothing
		                this.addInput(`${to_add_value}`, this._type, {shape: 7});
					});
				}
				break;
        }
    },
	async setup() {
		// to keep Set/Get node virtual connections visible when offscreen
		const originalComputeVisibleNodes = LGraphCanvas.prototype.computeVisibleNodes;
		LGraphCanvas.prototype.computeVisibleNodes = function () {
			const visibleNodesSet = new Set(originalComputeVisibleNodes.apply(this, arguments));
			for (const node of this.graph._nodes) {
				if ((node.type === "SetNode" || node.type === "GetNode") && node.drawConnection) {
					visibleNodesSet.add(node);
				}
			}
			return Array.from(visibleNodesSet);
		};

	}
});
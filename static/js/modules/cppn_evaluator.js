/**
 * Lightweight JS-side CPPN evaluator.
 * Evaluates a feed-forward CPPN from genome JSON (nodes + connections).
 * Independent of the signal registry; works with any genome and input array.
 * Use for non-visual outputs (audio, data, haptics) without GPU readback.
 *
 * Exposes: window.CppnEvaluator.activate(genomeJson, numInputs, numOutputs, inputs) -> outputs[]
 */
(function () {
    "use strict";

    var ACTIVATIONS = {
        sigmoid: function (x) {
            return 1 / (1 + Math.exp(-x));
        },
        tanh: function (x) {
            return Math.tanh(x);
        },
        sin: function (x) {
            return Math.sin(x);
        },
        cos: function (x) {
            return Math.cos(x);
        },
        gauss: function (x) {
            return Math.exp(-x * x);
        },
        relu: function (x) {
            return x > 0 ? x : 0;
        },
        abs: function (x) {
            return Math.abs(x);
        },
        square: function (x) {
            return x * x;
        },
        cube: function (x) {
            return x * x * x;
        },
        identity: function (x) {
            return x;
        },
        clamped: function (x) {
            return x < -1 ? -1 : x > 1 ? 1 : x;
        },
        exp: function (x) {
            return Math.exp(x);
        },
        hat: function (x) {
            var a = Math.abs(x);
            return 1 - a > 0 ? 1 - a : 0;
        },
        inv: function (x) {
            if (Math.abs(x) < 0.001) return 0;
            return 1 / x;
        },
        log: function (x) {
            return Math.log(Math.abs(x) + 1e-10);
        },
    };

    function topologicalSort(numInputs, numOutputs, nodes, connections) {
        var inDegree = {};
        var adjacency = {};
        var allNodes = new Set();
        var i;
        for (i = -numInputs; i < 0; i++) allNodes.add(i);
        for (i = 0; i < numOutputs; i++) allNodes.add(i);
        Object.keys(nodes).forEach(function (k) {
            allNodes.add(parseInt(k, 10));
        });
        allNodes.forEach(function (n) {
            inDegree[n] = 0;
            adjacency[n] = [];
        });
        Object.keys(connections).forEach(function (key) {
            var c = connections[key];
            if (!c.enabled) return;
            var parts = key.split("_", 2);
            if (parts.length !== 2) return;
            var src = parseInt(parts[0], 10);
            var dst = parseInt(parts[1], 10);
            if (isNaN(src) || isNaN(dst)) return;
            adjacency[src].push(dst);
            inDegree[dst] = (inDegree[dst] || 0) + 1;
            allNodes.add(src);
            allNodes.add(dst);
        });
        var queue = [];
        allNodes.forEach(function (n) {
            if (inDegree[n] === 0) queue.push(n);
        });
        var sorted = [];
        while (queue.length) {
            var node = queue.shift();
            sorted.push(node);
            (adjacency[node] || []).forEach(function (neighbor) {
                inDegree[neighbor] -= 1;
                if (inDegree[neighbor] === 0) queue.push(neighbor);
            });
        }
        return sorted;
    }

    function activate(genomeJson, numInputs, numOutputs, inputs) {
        var nodes = genomeJson.nodes || {};
        var connections = genomeJson.connections || {};
        var sorted = topologicalSort(numInputs, numOutputs, nodes, connections);
        var values = {};
        var n;
        for (n = -numInputs; n < 0; n++) {
            values[n] = inputs[numInputs + n] != null ? inputs[numInputs + n] : 0;
        }
        var nodeInputs = {};
        Object.keys(connections).forEach(function (key) {
            var c = connections[key];
            if (!c.enabled) return;
            var parts = key.split("_", 2);
            if (parts.length !== 2) return;
            var src = parseInt(parts[0], 10);
            var dst = parseInt(parts[1], 10);
            if (isNaN(src) || isNaN(dst)) return;
            if (!nodeInputs[dst]) nodeInputs[dst] = [];
            nodeInputs[dst].push({ src: src, weight: c.weight });
        });
        sorted.forEach(function (nodeId) {
            if (nodeId < 0) return;
            var sum = 0;
            var inputsList = nodeInputs[nodeId];
            if (inputsList) {
                inputsList.forEach(function (e) {
                    sum += (values[e.src] != null ? values[e.src] : 0) * e.weight;
                });
            }
            var node = nodes[String(nodeId)];
            var bias = node && node.bias != null ? node.bias : 0;
            var response = node && node.response != null ? node.response : 1;
            var activation = node && node.activation ? node.activation : "identity";
            var fn = ACTIVATIONS[activation] || ACTIVATIONS.identity;
            values[nodeId] = fn((sum + bias) * response);
        });
        var out = [];
        for (n = 0; n < numOutputs; n++) {
            out.push(values[n] != null ? values[n] : 0);
        }
        return out;
    }

    window.CppnEvaluator = { activate: activate };
})();

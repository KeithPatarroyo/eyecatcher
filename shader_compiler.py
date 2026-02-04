"""
CPPN to GLSL Shader Compiler.
Converts NEAT genomes into GPU-executable shader code.

Supports dual-CPPN compilation where a time signal CPPN modulates
the time input to a visual CPPN.
"""
import neat
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from cppn_engine import DualGenome


class ShaderCompiler:
    """
    Compiles CPPN networks into GLSL fragment shader code.
    The shader can then be executed on GPU for real-time rendering.
    """
    
    # Map NEAT activation functions to GLSL
    ACTIVATION_FUNCTIONS = {
        'sigmoid': 'sigmoid',
        'tanh': 'tanh',
        'sin': 'sin',
        'cos': 'cos',
        'gauss': 'gauss',
        'relu': 'relu',
        'abs': 'abs',
        'square': 'square',
        'cube': 'cube',
        'identity': 'identity',
        'clamped': 'clamped',
        'exp': 'exp',
        'hat': 'hat',
        'inv': 'inv',
        'log': 'log',
    }
    
    def __init__(self):
        self.node_order: List[int] = []
        self.node_code: Dict[int, str] = {}
        
    def compile_to_glsl(self, genome: neat.DefaultGenome, config: neat.Config) -> str:
        """
        Compile a CPPN genome into GLSL shader code.
        
        Args:
            genome: NEAT genome to compile
            config: NEAT configuration
            
        Returns:
            Complete GLSL fragment shader code as string
        """
        # Analyze network topology
        connections = self._get_enabled_connections(genome)
        nodes = self._topological_sort(genome, connections, config)
        
        # Generate node computation code
        node_computations = self._generate_node_code(genome, connections, nodes, config)
        
        # Build complete shader
        shader = self._build_shader_template(node_computations, config)
        
        return shader
    
    def _get_enabled_connections(self, genome: neat.DefaultGenome) -> List[Tuple]:
        """Get all enabled connections in the genome."""
        return [(c.key[0], c.key[1], c.weight) 
                for c in genome.connections.values() if c.enabled]
    
    def _topological_sort(self, 
                         genome: neat.DefaultGenome, 
                         connections: List[Tuple],
                         config: neat.Config) -> List[int]:
        """
        Topologically sort nodes for correct evaluation order.
        
        Returns:
            List of node IDs in evaluation order
        """
        # Build adjacency list
        in_degree = {}
        adjacency = {}
        all_nodes = set()
        
        # Initialize with input nodes (IDs 0-4: x, y, distance, time, bias)
        num_inputs = config.genome_config.num_inputs
        input_nodes = list(range(-num_inputs, 0))
        
        # Output nodes (IDs starting from 0: R, G, B)
        num_outputs = config.genome_config.num_outputs
        output_nodes = list(range(num_outputs))
        
        all_nodes.update(input_nodes)
        all_nodes.update(output_nodes)
        all_nodes.update(genome.nodes.keys())
        
        # Initialize in-degree and adjacency
        for node in all_nodes:
            in_degree[node] = 0
            adjacency[node] = []
        
        # Build graph from connections
        for src, dst, weight in connections:
            adjacency[src].append(dst)
            in_degree[dst] += 1
            all_nodes.add(src)
            all_nodes.add(dst)
        
        # Topological sort using Kahn's algorithm
        queue = [node for node in all_nodes if in_degree[node] == 0]
        sorted_nodes = []
        
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return sorted_nodes
    
    def _generate_node_code(self,
                           genome: neat.DefaultGenome,
                           connections: List[Tuple],
                           nodes: List[int],
                           config: neat.Config,
                           input_names: Optional[Dict[int, str]] = None,
                           prefix: str = "") -> str:
        """Generate GLSL code for all node computations."""
        
        # Build connection map: node_id -> [(input_node, weight), ...]
        node_inputs = {}
        for src, dst, weight in connections:
            if dst not in node_inputs:
                node_inputs[dst] = []
            node_inputs[dst].append((src, weight))
        
        code_lines = []
        
        # Default input names for visual CPPN
        if input_names is None:
            input_names = {
                -6: 'vX',
                -5: 'vY', 
                -4: 'vDist',
                -3: 'vTime',
                -2: 'vMouseSpeed',
                -1: 'vBias'
            }
        
        node_vars = input_names.copy()
        
        # Generate code for each node
        for node_id in nodes:
            # Skip input nodes (already defined)
            if node_id in input_names:
                continue
            
            # Get node configuration
            if node_id in genome.nodes:
                node = genome.nodes[node_id]
                activation = node.activation
                bias = node.bias
                response = node.response
            else:
                # Output nodes use defaults
                activation = 'identity'
                bias = 0.0
                response = 1.0
            
            # Generate variable name with optional prefix
            if node_id >= config.genome_config.num_outputs:
                var_name = f"{prefix}node_{node_id}"
            else:
                var_name = f"{prefix}output_{node_id}"
            node_vars[node_id] = var_name
            
            # Compute weighted sum of inputs
            if node_id in node_inputs:
                input_terms = []
                for src_id, weight in node_inputs[node_id]:
                    src_var = node_vars.get(src_id, f"{prefix}node_{src_id}")
                    input_terms.append(f"{src_var} * {weight:.6f}")
                
                weighted_sum = " + ".join(input_terms)
                if bias != 0.0:
                    weighted_sum += f" + {bias:.6f}"
                
                # Apply activation function
                activation_func = self.ACTIVATION_FUNCTIONS.get(activation, 'identity')
                
                if response != 1.0:
                    code_lines.append(f"    float {var_name} = {activation_func}(({weighted_sum}) * {response:.6f});")
                else:
                    code_lines.append(f"    float {var_name} = {activation_func}({weighted_sum});")
            else:
                # Node with no inputs
                code_lines.append(f"    float {var_name} = {bias:.6f};")
        
        return "\n".join(code_lines)
    
    def _generate_time_signal_code(self,
                                   time_genome: neat.DefaultGenome,
                                   time_config: neat.Config) -> str:
        """Generate GLSL code for the time signal CPPN."""
        connections = self._get_enabled_connections(time_genome)
        nodes = self._topological_sort(time_genome, connections, time_config)
        
        # Time signal input names: raw_time, mouseSpeed, bias
        time_input_names = {
            -3: 'vRawTime',
            -2: 'vMouseSpeed',
            -1: 'vBias'
        }
        
        return self._generate_node_code(
            time_genome, connections, nodes, time_config,
            input_names=time_input_names,
            prefix="time_"
        )
    
    def _build_shader_template(self, node_code: str, config: neat.Config) -> str:
        """Build the complete GLSL shader with node computations (single CPPN)."""

        shader = f"""#version 300 es
precision highp float;

// Inputs from vertex shader
in vec2 vUV;  // UV coordinates (0-1)
uniform float uTime;  // Time uniform (0-1)
uniform float uMouseSpeed;  // Mouse movement speed (0-1)
uniform float uMouseX;  // Mouse X position (0-1)
uniform float uMouseY;  // Mouse Y position (0-1)
uniform float uPerturbStrength;  // Perturbation strength (0-1)

// Output color
out vec4 fragColor;

// Activation functions
float sigmoid(float x) {{
    return 1.0 / (1.0 + exp(-x));
}}

float gauss(float x) {{
    return exp(-x * x);
}}

float relu(float x) {{
    return max(0.0, x);
}}

float square(float x) {{
    return x * x;
}}

float cube(float x) {{
    return x * x * x;
}}

float identity(float x) {{
    return x;
}}

float clamped(float x) {{
    return clamp(x, -1.0, 1.0);
}}

float hat(float x) {{
    return max(0.0, 1.0 - abs(x));
}}

float inv(float x) {{
    if (abs(x) < 0.001) return 0.0;
    return 1.0 / x;
}}

void main() {{
    // Convert UV to CPPN coordinate space (-1 to 1)
    float vX = vUV.x * 2.0 - 1.0;
    float vY = vUV.y * 2.0 - 1.0;

    // Mouse position in CPPN coordinate space
    float mX = uMouseX * 2.0 - 1.0;
    float mY = uMouseY * 2.0 - 1.0;

    // Distance from current pixel to mouse position
    float mouseDistX = vX - mX;
    float mouseDistY = vY - mY;
    float mouseDist = sqrt(mouseDistX * mouseDistX + mouseDistY * mouseDistY);

    // Perturbation field: Gaussian blob centered at mouse
    // Creates a wave-like disturbance that affects local coordinates
    float perturbRadius = 0.4;
    float perturbField = exp(-mouseDist * mouseDist / (perturbRadius * perturbRadius));
    float perturbAmount = perturbField * uPerturbStrength;

    // Apply perturbation: shift coordinates based on mouse proximity
    // This creates a "lens" or "ripple" effect emanating from cursor
    float ripple = sin(mouseDist * 10.0 - uTime * 6.28) * perturbAmount * 0.3;
    vX = vX + mouseDistX * ripple;
    vY = vY + mouseDistY * ripple;

    // Recalculate distance after perturbation
    float vDist = sqrt(vX * vX + vY * vY);

    // Time with local perturbation (mouse can speed up/slow down local time)
    float vTime = uTime * 2.0 - 1.0 + perturbAmount * 0.5;
    float vMouseSpeed = uMouseSpeed * 2.0 - 1.0;
    float vBias = 1.0;

    // Network computations
{node_code}

    // Output RGB (clamp to 0-1)
    float r = clamp((output_0 + 1.0) * 0.5, 0.0, 1.0);
    float g = clamp((output_1 + 1.0) * 0.5, 0.0, 1.0);
    float b = clamp((output_2 + 1.0) * 0.5, 0.0, 1.0);

    fragColor = vec4(r, g, b, 1.0);
}}
"""
        return shader
    
    def compile_dual_to_glsl(self,
                             dual_genome: 'DualGenome',
                             visual_config: neat.Config,
                             time_config: neat.Config) -> str:
        """
        Compile a dual CPPN (time signal + visual) into GLSL shader code.
        
        The time signal CPPN transforms the raw time based on mouse speed,
        then the visual CPPN uses this modified time to generate colors.
        
        Args:
            dual_genome: DualGenome containing visual and time_signal genomes
            visual_config: NEAT configuration for visual CPPN
            time_config: NEAT configuration for time signal CPPN
            
        Returns:
            Complete GLSL fragment shader code as string
        """
        # Generate time signal network code
        time_code = self._generate_time_signal_code(
            dual_genome.time_signal, time_config
        )
        
        # Generate visual network code  
        visual_connections = self._get_enabled_connections(dual_genome.visual)
        visual_nodes = self._topological_sort(
            dual_genome.visual, visual_connections, visual_config
        )
        visual_code = self._generate_node_code(
            dual_genome.visual, visual_connections, visual_nodes, visual_config
        )
        
        # Build the dual shader
        shader = self._build_dual_shader_template(time_code, visual_code)
        
        return shader
    
    def _build_dual_shader_template(self, time_code: str, visual_code: str) -> str:
        """Build the complete GLSL shader for dual CPPN (time signal + visual)."""

        shader = f"""#version 300 es
precision highp float;

// Inputs from vertex shader
in vec2 vUV;  // UV coordinates (0-1)
uniform float uTime;  // Time uniform (0-1)
uniform float uMouseSpeed;  // Mouse movement speed (0-1)
uniform float uMouseX;  // Mouse X position (0-1)
uniform float uMouseY;  // Mouse Y position (0-1)
uniform float uPerturbStrength;  // Perturbation strength (0-1)

// Output color
out vec4 fragColor;

// Activation functions
float sigmoid(float x) {{
    return 1.0 / (1.0 + exp(-x));
}}

float gauss(float x) {{
    return exp(-x * x);
}}

float relu(float x) {{
    return max(0.0, x);
}}

float square(float x) {{
    return x * x;
}}

float cube(float x) {{
    return x * x * x;
}}

float identity(float x) {{
    return x;
}}

float clamped(float x) {{
    return clamp(x, -1.0, 1.0);
}}

float hat(float x) {{
    return max(0.0, 1.0 - abs(x));
}}

float inv(float x) {{
    if (abs(x) < 0.001) return 0.0;
    return 1.0 / x;
}}

void main() {{
    // Mouse position in CPPN coordinate space
    float mX = uMouseX * 2.0 - 1.0;
    float mY = uMouseY * 2.0 - 1.0;

    // Base coordinates
    float baseX = vUV.x * 2.0 - 1.0;
    float baseY = vUV.y * 2.0 - 1.0;

    // Distance from current pixel to mouse position
    float mouseDistX = baseX - mX;
    float mouseDistY = baseY - mY;
    float mouseDist = sqrt(mouseDistX * mouseDistX + mouseDistY * mouseDistY);

    // Perturbation field: Gaussian blob centered at mouse
    float perturbRadius = 0.4;
    float perturbField = exp(-mouseDist * mouseDist / (perturbRadius * perturbRadius));
    float perturbAmount = perturbField * uPerturbStrength;

    // Raw inputs
    float vRawTime = uTime * 2.0 - 1.0;
    float vMouseSpeed = uMouseSpeed * 2.0 - 1.0;
    float vBias = 1.0;

    // === TIME SIGNAL NETWORK ===
    // Transforms raw time based on mouse speed
{time_code}

    // Get modified time from time signal network (clamped to valid range)
    float vTime = clamp(time_output_0, -1.0, 1.0);

    // Add local time perturbation from mouse (creates local "time bubbles")
    vTime = vTime + perturbAmount * 0.5;

    // === VISUAL NETWORK ===
    // Convert UV to CPPN coordinate space with perturbation
    float ripple = sin(mouseDist * 10.0 - uTime * 6.28) * perturbAmount * 0.3;
    float vX = baseX + mouseDistX * ripple;
    float vY = baseY + mouseDistY * ripple;
    float vDist = sqrt(vX * vX + vY * vY);

    // Visual network computations (using modified time)
{visual_code}

    // Output RGB (clamp to 0-1)
    float r = clamp((output_0 + 1.0) * 0.5, 0.0, 1.0);
    float g = clamp((output_1 + 1.0) * 0.5, 0.0, 1.0);
    float b = clamp((output_2 + 1.0) * 0.5, 0.0, 1.0);

    fragColor = vec4(r, g, b, 1.0);
}}
"""
        return shader
    
    def export_shader_bundle(self, 
                            genome: neat.DefaultGenome, 
                            config: neat.Config,
                            filepath: str):
        """
        Export shader code and metadata as a JSON bundle.
        
        Args:
            genome: NEAT genome
            config: NEAT configuration
            filepath: Output file path
        """
        shader_code = self.compile_to_glsl(genome, config)
        
        bundle = {
            "shader": shader_code,
            "metadata": {
                "num_nodes": len(genome.nodes),
                "num_connections": len([c for c in genome.connections.values() if c.enabled]),
                "fitness": getattr(genome, 'fitness', None)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(bundle, f, indent=2)
    
    def export_dual_shader_bundle(self,
                                  dual_genome: 'DualGenome',
                                  visual_config: neat.Config,
                                  time_config: neat.Config,
                                  filepath: str):
        """
        Export dual CPPN shader code and metadata as a JSON bundle.
        
        Args:
            dual_genome: DualGenome containing visual and time_signal genomes
            visual_config: NEAT configuration for visual CPPN
            time_config: NEAT configuration for time signal CPPN
            filepath: Output file path
        """
        shader_code = self.compile_dual_to_glsl(dual_genome, visual_config, time_config)
        
        bundle = {
            "shader": shader_code,
            "metadata": {
                "type": "dual_cppn",
                "visual": {
                    "num_nodes": len(dual_genome.visual.nodes),
                    "num_connections": len([c for c in dual_genome.visual.connections.values() if c.enabled])
                },
                "time_signal": {
                    "num_nodes": len(dual_genome.time_signal.nodes),
                    "num_connections": len([c for c in dual_genome.time_signal.connections.values() if c.enabled])
                },
                "fitness": dual_genome.fitness
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(bundle, f, indent=2)

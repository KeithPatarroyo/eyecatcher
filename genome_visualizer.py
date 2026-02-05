"""
Genome Visualization
Visualizes CPPN network structure using matplotlib
"""
import neat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from typing import Dict, List, Tuple, Optional, Set


class GenomeVisualizer:
    """Visualizes NEAT genome network structure."""
    
    # Color scheme
    COLORS = {
        'input': '#4A90E2',      # Blue
        'hidden': '#50C878',     # Green
        'output': '#E74C3C',     # Red
        'enabled': '#2C3E50',    # Dark gray
        'disabled': '#BDC3C7',   # Light gray
        'positive': '#27AE60',   # Green
        'negative': '#E74C3C',   # Red
    }
    
    def __init__(self, config: neat.Config):
        """Initialize visualizer with NEAT config."""
        self.config = config
        self.num_inputs = config.genome_config.num_inputs
        self.num_outputs = config.genome_config.num_outputs
        
    def visualize_genome(self, 
                        genome: neat.DefaultGenome, 
                        filepath: str,
                        view: bool = False,
                        figsize: Tuple[int, int] = (12, 8)):
        """
        Create a visualization of the genome network structure.
        
        Args:
            genome: NEAT genome to visualize
            filepath: Output file path (PDF)
            view: Whether to display the plot
            figsize: Figure size (width, height)
        """
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(-0.5, 1.5)
        ax.axis('off')
        
        # Calculate node positions
        positions = self._calculate_positions(genome)
        
        # Draw connections first (so they appear behind nodes)
        self._draw_connections(ax, genome, positions)
        
        # Draw nodes
        self._draw_nodes(ax, genome, positions)
        
        # Add title and legend
        self._add_title_and_legend(ax, genome)
        
        # Save as vector PDF
        plt.tight_layout()
        plt.savefig(filepath, format='pdf', bbox_inches='tight', facecolor='white')
        
        if view:
            plt.show()
        else:
            plt.close()
    
    def _calculate_positions(self, genome: neat.DefaultGenome) -> Dict[int, Tuple[float, float]]:
        """Calculate (x, y) positions for all nodes."""
        positions = {}
        
        # Input nodes on left
        input_ids = list(range(-self.num_inputs, 0))
        input_names = ['x', 'y', 'distance', 'angle', 'sin(a)', 'cos(a)', 'time', 'bias']
        for i, node_id in enumerate(input_ids):
            y = 1.0 - (i / max(1, self.num_inputs - 1)) if self.num_inputs > 1 else 0.5
            positions[node_id] = (0.0, y)
        
        # Output nodes on right
        output_ids = list(range(self.num_outputs))
        output_names = ['R', 'G', 'B']
        for i, node_id in enumerate(output_ids):
            y = 1.0 - (i / max(1, self.num_outputs - 1)) if self.num_outputs > 1 else 0.5
            positions[node_id] = (1.0, y)
        
        # Hidden nodes in middle (layered)
        hidden_nodes = list(genome.nodes.keys())
        if hidden_nodes:
            # Use simple layering based on connectivity
            layers = self._assign_layers(genome, input_ids, output_ids)
            
            for node_id, layer in layers.items():
                nodes_in_layer = [n for n, l in layers.items() if l == layer]
                idx = nodes_in_layer.index(node_id)
                
                # X position based on layer
                x = 0.3 + (layer * 0.4 / max(1, max(layers.values())))
                
                # Y position distributed evenly
                if len(nodes_in_layer) == 1:
                    y = 0.5
                else:
                    y = 1.0 - (idx / (len(nodes_in_layer) - 1))
                
                positions[node_id] = (x, y)
        
        return positions
    
    def _assign_layers(self, 
                      genome: neat.DefaultGenome,
                      input_ids: List[int],
                      output_ids: List[int]) -> Dict[int, int]:
        """Assign hidden nodes to layers based on connectivity."""
        layers = {}
        
        # Get all connections
        connections = [(c.key[0], c.key[1]) for c in genome.connections.values() if c.enabled]
        
        # Build adjacency
        adjacency = {}
        for src, dst in connections:
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(dst)
        
        # BFS from inputs to assign layers
        visited = set()
        queue = [(node_id, 0) for node_id in input_ids]
        
        while queue:
            node_id, layer = queue.pop(0)
            
            if node_id in visited:
                continue
            visited.add(node_id)
            
            # Only track hidden nodes
            if node_id not in input_ids and node_id not in output_ids:
                layers[node_id] = layer
            
            # Add neighbors
            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    queue.append((neighbor, layer + 1))
        
        # Normalize layers to 0-based
        if layers:
            min_layer = min(layers.values())
            layers = {k: v - min_layer for k, v in layers.items()}
        
        return layers
    
    def _get_nodes_required_for_output(self, genome: neat.DefaultGenome) -> Set[int]:
        """
        Find all nodes that are required to compute outputs (backward trace from outputs).
        Returns set of node IDs that contribute to at least one output.
        """
        output_ids = list(range(self.num_outputs))
        
        # Build reverse adjacency (who feeds into each node)
        reverse_adjacency = {}
        for conn in genome.connections.values():
            if conn.enabled:
                src, dst = conn.key
                if dst not in reverse_adjacency:
                    reverse_adjacency[dst] = []
                reverse_adjacency[dst].append(src)
        
        # Backward BFS from outputs
        required = set(output_ids)
        queue = list(output_ids)
        visited = set()
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            
            # Add all nodes that feed into this node
            for src in reverse_adjacency.get(node_id, []):
                required.add(src)
                if src not in visited:
                    queue.append(src)
        
        return required
    
    def _draw_connections(self, 
                         ax, 
                         genome: neat.DefaultGenome,
                         positions: Dict[int, Tuple[float, float]]):
        """Draw connections between nodes."""
        for conn in genome.connections.values():
            src_id, dst_id = conn.key
            
            if src_id not in positions or dst_id not in positions:
                continue
            
            src_pos = positions[src_id]
            dst_pos = positions[dst_id]
            
            # Connection style
            if conn.enabled:
                alpha = 0.6
                linestyle = '-'
            else:
                alpha = 0.2
                linestyle = '--'
            
            # Color based on weight
            color = self.COLORS['positive'] if conn.weight >= 0 else self.COLORS['negative']
            
            # Line width based on weight magnitude
            linewidth = min(3, 0.5 + abs(conn.weight) / 5)
            
            # Draw arrow
            arrow = FancyArrowPatch(
                src_pos, dst_pos,
                arrowstyle='->,head_width=0.3,head_length=0.3',
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                linestyle=linestyle,
                connectionstyle='arc3,rad=0.1'
            )
            ax.add_patch(arrow)
    
    def _draw_nodes(self,
                   ax,
                   genome: neat.DefaultGenome,
                   positions: Dict[int, Tuple[float, float]]):
        """Draw nodes."""
        input_names = ['x', 'y', 'distance', 'angle', 'sin(a)', 'cos(a)', 'time', 'bias']
        output_names = ['R', 'G', 'B']
        
        # Identify which nodes are connected to outputs (active nodes)
        active_nodes = self._get_nodes_required_for_output(genome)
        
        for node_id, (x, y) in positions.items():
            # Check if node is active (contributes to output)
            is_active = node_id in active_nodes
            
            # Determine node type and style
            if node_id < 0:
                # Input node
                color = self.COLORS['input']
                size = 800
                idx = node_id + self.num_inputs
                label = input_names[idx] if idx < len(input_names) else str(node_id)
            elif node_id < self.num_outputs:
                # Output node
                color = self.COLORS['output']
                size = 800
                # Check if output node has custom config or use default
                if node_id in genome.nodes:
                    activation = genome.nodes[node_id].activation
                    label = f"{output_names[node_id]}\n{activation}" if node_id < len(output_names) else f"{node_id}\n{activation}"
                else:
                    # Output node not in genome.nodes, uses default (typically identity)
                    label = f"{output_names[node_id]}\nidentity" if node_id < len(output_names) else f"{node_id}\nidentity"
            else:
                # Hidden node
                color = self.COLORS['hidden']
                size = 700
                node = genome.nodes[node_id]
                label = f"{node_id}\n{node.activation}"
            
            # Set transparency based on whether node is active
            alpha = 0.9 if is_active else 0.2
            
            # Draw node circle
            ax.scatter(x, y, s=size, c=color, edgecolors='white', 
                      linewidths=2, zorder=10, alpha=alpha)
            
            # Add label with appropriate transparency
            label_alpha = 1.0 if is_active else 0.3
            ax.text(x, y, label, ha='center', va='center',
                   fontsize=10, fontweight='bold', color='white', zorder=11, alpha=label_alpha)
    
    def _add_title_and_legend(self, ax, genome: neat.DefaultGenome):
        """Add title and legend to the plot."""
        # Count statistics
        num_hidden = len(genome.nodes)
        num_connections = len([c for c in genome.connections.values() if c.enabled])
        num_disabled = len([c for c in genome.connections.values() if not c.enabled])
        
        # Title
        title = f"CPPN Genome #{genome.key}\n"
        title += f"Nodes: {self.num_inputs} inputs + {num_hidden} hidden + {self.num_outputs} outputs\n"
        title += f"Connections: {num_connections} enabled, {num_disabled} disabled"
        ax.text(0.5, 1.05, title, transform=ax.transAxes,
               ha='center', fontsize=11, fontweight='bold')
        
        # Legend
        legend_elements = [
            mpatches.Patch(color=self.COLORS['input'], label='Input Nodes'),
            mpatches.Patch(color=self.COLORS['hidden'], label='Hidden Nodes'),
            mpatches.Patch(color=self.COLORS['output'], label='Output Nodes'),
            mpatches.Patch(color=self.COLORS['positive'], label='Positive Weight'),
            mpatches.Patch(color=self.COLORS['negative'], label='Negative Weight'),
        ]
        ax.legend(handles=legend_elements, loc='upper left', 
                 bbox_to_anchor=(0, -0.05), ncol=5, frameon=False)

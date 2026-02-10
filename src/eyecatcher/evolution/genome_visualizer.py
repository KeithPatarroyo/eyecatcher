"""
Genome Visualization
Visualizes CPPN network structure using matplotlib
"""

import io
import logging
from typing import BinaryIO, Optional, Union

import matplotlib

matplotlib.use("Agg")  # must be before importing pyplot

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import neat  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

from .signals import VISUAL_INPUTS, VISUAL_OUTPUTS, input_names, output_labels

logger = logging.getLogger(__name__)


class GenomeVisualizer:
    """Visualizes NEAT genome network structure."""

    # Node size for all circles
    NODE_SIZE = 2000

    # Color scheme
    COLORS = {
        "input": "#4A90E2",  # Blue
        "hidden": "#50C878",  # Green
        "output": "#E74C3C",  # Red
        "enabled": "#2C3E50",  # Dark gray
        "disabled": "#BDC3C7",  # Light gray
        "positive": "#27AE60",  # Green
        "negative": "#E74C3C",  # Red
    }

    def __init__(self, visual_config: neat.Config):
        """Initialize visualizer with NEAT config (visual CPPN)."""
        self.config = visual_config
        self.num_inputs = visual_config.genome_config.num_inputs
        self.num_outputs = visual_config.genome_config.num_outputs

    def visualize_genome(
        self,
        genome: neat.DefaultGenome,
        output: Union[str, BinaryIO],
        view: bool = False,
        figsize: Optional[tuple] = None,
    ):
        """
        Create a visualization of the genome network structure.

        Args:
            genome: NEAT genome to visualize
            output: Output file path (str) or file-like object (e.g. BytesIO) for PDF
            view: Whether to display the plot
            figsize: (width, height). If None, auto from node count.
        """
        # Calculate max nodes in any column for sizing
        max_nodes_in_column = max(self.num_inputs, self.num_outputs)
        hidden_nodes = [
            n for n in genome.nodes.keys() if n not in range(self.num_outputs)
        ]
        if hidden_nodes:
            layers = self._assign_layers(
                genome, list(range(-self.num_inputs, 0)), list(range(self.num_outputs))
            )
            if layers:
                layer_counts = {}
                for layer in layers.values():
                    layer_counts[layer] = layer_counts.get(layer, 0) + 1
                max_nodes_in_column = max(
                    max_nodes_in_column, max(layer_counts.values())
                )

        # Dynamic figure size: ensure enough vertical space per node
        # With NODE_SIZE=2000, we need about 1.0 units per node vertically
        if figsize is None:
            height = max(6, max_nodes_in_column * 1.0)
            figsize = (12, height)

        fig, ax = plt.subplots(figsize=figsize, facecolor="white")

        # Calculate node positions first
        positions = self._calculate_positions(genome)

        # Set axis limits based on actual node positions (auto-fit to content)
        if positions:
            y_values = [pos[1] for pos in positions.values()]
            y_min, y_max = min(y_values), max(y_values)
            # Add small padding for node radius (about 0.15 units for NODE_SIZE=2000)
            padding = 0.18
            ax.set_xlim(-0.3, 1.3)
            ax.set_ylim(y_min - padding, y_max + padding)
        else:
            ax.set_xlim(-0.3, 1.3)
            ax.set_ylim(0, 1)
        ax.axis("off")

        # Draw connections first (so they appear behind nodes)
        self._draw_connections(ax, genome, positions)

        # Draw nodes
        self._draw_nodes(ax, genome, positions)

        # Add title and legend
        self._add_title_and_legend(ax, genome)

        # Save as vector PDF - bbox_inches='tight' auto-crops whitespace
        plt.savefig(
            output,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0.05,
            facecolor="white",
        )

        if view:
            plt.show()
        else:
            plt.close()

    @staticmethod
    def _position_column(node_ids: list, x: float, node_spacing: float) -> dict:
        """Place nodes in a column at x with vertical spacing; returns {id: (x, y)}."""
        if not node_ids:
            return {}
        n = len(node_ids)
        total_height = (n - 1) * node_spacing
        start_y = total_height / 2
        return {
            node_id: (x, 0.5 + start_y - (i * node_spacing))
            for i, node_id in enumerate(node_ids)
        }

    def _calculate_positions(self, genome: neat.DefaultGenome) -> dict:
        """Calculate (x, y) positions for all nodes with equal spacing."""
        node_spacing = 0.25
        positions = {}

        input_ids = list(range(-self.num_inputs, 0))
        positions.update(self._position_column(input_ids, 0.0, node_spacing))
        output_ids = list(range(self.num_outputs))
        positions.update(self._position_column(output_ids, 1.0, node_spacing))

        hidden_nodes = [n for n in genome.nodes.keys() if n not in output_ids]
        if hidden_nodes:
            layers = self._assign_layers(genome, input_ids, output_ids)
            if layers:
                num_layers = max(layers.values()) + 1
                layer_groups: dict = {}
                for node_id, layer in layers.items():
                    layer_groups.setdefault(layer, []).append(node_id)
                for layer, nodes_in_layer in sorted(layer_groups.items()):
                    nodes_in_layer.sort()
                    x = 0.2 + (layer + 1) * 0.6 / (num_layers + 1)
                    positions.update(
                        self._position_column(nodes_in_layer, x, node_spacing)
                    )
        return positions

    def _assign_layers(
        self, genome: neat.DefaultGenome, input_ids: list, output_ids: list
    ) -> dict:
        """Assign hidden nodes to layers based on connectivity."""
        layers = {}

        # Get all connections
        connections = [
            (c.key[0], c.key[1]) for c in genome.connections.values() if c.enabled
        ]

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

    def _get_nodes_required_for_output(self, genome: neat.DefaultGenome) -> set:
        """
        Find nodes required to compute outputs (backward trace from outputs).
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

    def _draw_connections(self, ax, genome: neat.DefaultGenome, positions: dict):
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
                linestyle = "-"
            else:
                alpha = 0.2
                linestyle = "--"

            # Color based on weight
            color = (
                self.COLORS["positive"] if conn.weight >= 0 else self.COLORS["negative"]
            )

            # Line width based on weight magnitude
            linewidth = min(3, 0.5 + abs(conn.weight) / 5)

            # Draw straight arrow
            arrow = FancyArrowPatch(
                src_pos,
                dst_pos,
                arrowstyle="->,head_width=0.3,head_length=0.3",
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                linestyle=linestyle,
                connectionstyle="arc3,rad=0",  # rad=0 for straight lines
            )
            ax.add_patch(arrow)

    def _draw_nodes(self, ax, genome: neat.DefaultGenome, positions: dict):
        """Draw nodes."""
        input_name_list = input_names(VISUAL_INPUTS)
        output_name_list = output_labels(VISUAL_OUTPUTS)

        # Identify which nodes are connected to outputs (active nodes)
        active_nodes = self._get_nodes_required_for_output(genome)

        for node_id, (x, y) in positions.items():
            # Check if node is active (contributes to output)
            is_active = node_id in active_nodes

            # Determine node type and style
            if node_id < 0:
                # Input node
                color = self.COLORS["input"]
                idx = node_id + self.num_inputs
                label = (
                    input_name_list[idx] if idx < len(input_name_list) else str(node_id)
                )
            elif node_id < self.num_outputs:
                # Output node
                color = self.COLORS["output"]
                # Check if output node has custom config or use default
                if node_id in genome.nodes:
                    activation = genome.nodes[node_id].activation
                    label = (
                        f"{output_name_list[node_id]}\n{activation}"
                        if node_id < len(output_name_list)
                        else f"{node_id}\n{activation}"
                    )
                else:
                    # Output node not in genome.nodes, uses default (typically identity)
                    label = (
                        f"{output_name_list[node_id]}\nidentity"
                        if node_id < len(output_name_list)
                        else f"{node_id}\nidentity"
                    )
            else:
                # Hidden node
                color = self.COLORS["hidden"]
                node = genome.nodes[node_id]
                label = f"{node_id}\n{node.activation}"

            # Set transparency based on whether node is active
            alpha = 0.9 if is_active else 0.2

            # Draw node circle
            ax.scatter(
                x,
                y,
                s=self.NODE_SIZE,
                c=color,
                edgecolors="white",
                linewidths=2,
                zorder=10,
                alpha=alpha,
            )

            # Add label with appropriate transparency
            label_alpha = 1.0 if is_active else 0.3
            ax.text(
                x,
                y,
                label,
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="black",
                zorder=11,
                alpha=label_alpha,
            )

    def _add_title_and_legend(self, ax, genome: neat.DefaultGenome):
        """Add title and legend to the plot."""
        # Count statistics
        num_hidden = len(genome.nodes) - self.num_outputs
        num_connections = len([c for c in genome.connections.values() if c.enabled])
        num_disabled = len([c for c in genome.connections.values() if not c.enabled])

        # Title - positioned closer to plot
        title = f"CPPN Genome #{genome.key}  |  "
        title += (
            f"Nodes: {self.num_inputs}in + {num_hidden}hid + {self.num_outputs}out  |  "
        )
        title += f"Connections: {num_connections} enabled, {num_disabled} disabled"
        ax.set_title(title, fontsize=10, fontweight="bold", pad=10)

        # Legend - positioned closer to plot
        legend_elements = [
            mpatches.Patch(color=self.COLORS["input"], label="Input"),
            mpatches.Patch(color=self.COLORS["hidden"], label="Hidden"),
            mpatches.Patch(color=self.COLORS["output"], label="Output"),
            mpatches.Patch(color=self.COLORS["positive"], label="+Weight"),
            mpatches.Patch(color=self.COLORS["negative"], label="-Weight"),
        ]
        ax.legend(
            handles=legend_elements,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=5,
            frameon=False,
            fontsize=9,
        )


def render_genome_network_pdf(
    genome: neat.DefaultGenome,
    visual_config: neat.Config,
    output: Union[str, BinaryIO],
) -> Optional[bytes]:
    """
    Render a genome network to PDF (optional matplotlib).

    Handles ImportError and other exceptions; logs and returns None on failure.
    If output is a path (str), writes to file and returns None.
    If output is a file-like (e.g. BytesIO), writes to it and returns its bytes.

    Returns:
        PDF bytes when output is file-like, else None.
    """
    try:
        visualizer = GenomeVisualizer(visual_config)
        visualizer.visualize_genome(genome, output)
        if isinstance(output, io.BytesIO):
            return output.getvalue()
        return None
    except ImportError:
        logger.warning("Could not visualize genome. Install matplotlib.")
        return None
    except Exception as e:
        logger.warning("Genome visualization failed: %s", e)
        return None

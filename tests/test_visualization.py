"""
Test genome visualization
"""
from cppn_engine import CPPNEngine, create_random_genome
from genome_visualizer import GenomeVisualizer
import os
import neat


def save_genome_as_text(genome: neat.DefaultGenome, filepath: str, config: neat.Config):
    """
    Save a genome to a human-readable text file for debugging.
    
    Args:
        genome: NEAT genome to save
        filepath: Output file path
        config: NEAT configuration
    """
    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    input_names = ['x', 'y', 'distance', 'angle', 'sin(a)', 'cos(a)', 'time', 'bias']
    output_names = ['R', 'G', 'B']
    
    with open(filepath, 'w') as f:
        f.write(f"Genome ID: {genome.key}\n")
        f.write(f"Fitness: {genome.fitness}\n")
        
        # Input/Output node info
        f.write(f"\nInputs: {num_inputs} (nodes -{num_inputs} to -1: {', '.join(input_names[:num_inputs])})\n")
        f.write(f"Outputs: {num_outputs} (nodes 0 to {num_outputs-1}: {', '.join(output_names[:num_outputs])})\n")
        
        f.write(f"\n{'='*60}\n")
        f.write(f"NODES ({len(genome.nodes)} hidden nodes)\n")
        f.write(f"{'='*60}\n\n")
        
        for node_id, node in sorted(genome.nodes.items()):
            f.write(f"Node {node_id}:\n")
            f.write(f"  Activation: {node.activation}\n")
            f.write(f"  Bias: {node.bias:.6f}\n")
            f.write(f"  Response: {node.response:.6f}\n")
            f.write(f"  Aggregation: {node.aggregation}\n\n")
        
        f.write(f"{'='*60}\n")
        f.write(f"CONNECTIONS ({len(genome.connections)} total)\n")
        f.write(f"{'='*60}\n\n")
        
        enabled_conns = [c for c in genome.connections.values() if c.enabled]
        disabled_conns = [c for c in genome.connections.values() if not c.enabled]
        
        # Group connections by destination (to show what feeds each node)
        f.write(f"Enabled ({len(enabled_conns)}):\n")
        
        # Show connections grouped by destination
        conn_by_dest = {}
        for conn in enabled_conns:
            src, dst = conn.key
            if dst not in conn_by_dest:
                conn_by_dest[dst] = []
            conn_by_dest[dst].append((src, conn.weight))
        
        for dst in sorted(conn_by_dest.keys()):
            # Determine destination type
            if dst < 0:
                dst_label = f"Input {dst}"
            elif dst < num_outputs:
                dst_label = f"Output {dst} ({output_names[dst]})"
            else:
                dst_label = f"Hidden {dst}"
            
            f.write(f"\n  -> {dst_label}:\n")
            for src, weight in sorted(conn_by_dest[dst]):
                # Determine source type
                if src < 0:
                    idx = src + num_inputs
                    if 0 <= idx < len(input_names):
                        src_label = input_names[idx]
                    else:
                        src_label = f"in{src}"
                elif src < num_outputs:
                    src_label = f"Output{src}"
                else:
                    src_label = f"Node{src}"
                
                f.write(f"    {src_label} ({src}): weight={weight:.6f}\n")
        
        if disabled_conns:
            f.write(f"\nDisabled ({len(disabled_conns)}):\n")
            for conn in sorted(disabled_conns, key=lambda c: c.key):
                src, dst = conn.key
                f.write(f"  {src} -> {dst}: weight={conn.weight:.6f}\n")


def test_visualization():
    """Test genome visualization feature."""
    print("Testing genome visualization...")
    
    # Create engine
    engine = CPPNEngine()
    engine.create_population()
    
    # Create a random genome
    genome = create_random_genome(engine.config, genome_id=42)
    
    # Add some mutations to make it interesting
    for _ in range(10):
        genome = engine.mutate_genome(genome)
    
    # Create output directory
    os.makedirs('output/test', exist_ok=True)
    
    # Save with visualization
    print("Saving genome with visualization...")
    engine.save_genome(genome, 'output/test/test_genome.pkl', visualize=True)
    
    # Save text representation for debugging
    print("Saving text representation...")
    save_genome_as_text(genome, 'output/test/test_genome.txt', engine.config)
    
    # Also render the pattern
    print("Rendering pattern image...")
    from PIL import Image
    img = engine.render_image(genome, resolution=128, time=0.5)
    Image.fromarray(img).save('output/test/test_pattern.png')
    
    print("\n" + "="*60)
    print("✓ Visualization test complete!")
    print("="*60)
    print("\nGenerated files:")
    print("  - output/test/test_genome.pkl (genome data)")
    print("  - output/test/test_genome.txt (human-readable text format)")
    print("  - output/test/test_genome_network.pdf (network visualization - vector PDF)")
    print("  - output/test/test_pattern.png (rendered pattern)")
    print("\nOpen the network visualization to see the CPPN structure!")
    print("="*60)

if __name__ == '__main__':
    test_visualization()

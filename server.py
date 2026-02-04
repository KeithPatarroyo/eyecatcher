"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding.

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)
"""
import os
import random

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from cppn_engine import CPPNEngine, DualGenome, create_random_dual_genome
from shader_compiler import ShaderCompiler

app = Flask(__name__)
CORS(app)

# Global state
engine = CPPNEngine()
engine.create_population()  # Initialize NEAT populations
compiler = ShaderCompiler()

current_population = []
current_generation = 0
genome_counter = 0


def create_population(size=12):
    """Create initial random population of dual genomes."""
    global current_population, genome_counter
    current_population = []
    
    for i in range(size):
        dual_genome = create_random_dual_genome(engine, genome_id=genome_counter)
        genome_counter += 1
        current_population.append({
            'id': dual_genome.key,
            'genome': dual_genome,
            'fitness': 0,
            'clicks': 0
        })
    
    return current_population


def breed_next_generation(parents, population_size=12):
    """Breed new generation of dual genomes from selected parents."""
    global current_population, genome_counter
    
    new_population = []
    
    # Elitism: keep best parent
    best_parent = max(parents, key=lambda x: x['clicks'])
    # Create a fresh copy to avoid mutation side effects
    elite = DualGenome(
        visual=best_parent['genome'].visual,
        time_signal=best_parent['genome'].time_signal,
        key=best_parent['genome'].key
    )
    new_population.append({
        'id': elite.key,
        'genome': elite,
        'fitness': 0,
        'clicks': 0
    })
    
    # Generate offspring
    while len(new_population) < population_size:
        if len(parents) == 1:
            # Only one parent: mutate
            child = engine.mutate_dual_genome(parents[0]['genome'], genome_counter)
        else:
            # Multiple parents: 70% mutation, 30% crossover
            if random.random() < 0.7:
                parent = random.choice(parents)
                child = engine.mutate_dual_genome(parent['genome'], genome_counter)
            else:
                p1, p2 = random.sample(parents, 2)
                child = engine.crossover_dual_genomes(
                    p1['genome'], p2['genome'], genome_counter
                )
        
        genome_counter += 1
        
        new_population.append({
            'id': child.key,
            'genome': child,
            'fitness': 0,
            'clicks': 0
        })
    
    current_population = new_population
    return current_population


@app.route('/')
def index():
    """Serve the viewer HTML."""
    return send_from_directory('.', 'interactive_viewer.html')


@app.route('/api/init', methods=['POST'])
def init_population():
    """Initialize new population."""
    global current_generation
    data = request.json or {}
    size = data.get('size', 12)
    
    current_generation = 0
    create_population(size)
    
    return jsonify({
        'generation': current_generation,
        'population_size': len(current_population),
        'status': 'initialized'
    })


@app.route('/api/population', methods=['GET'])
def get_population():
    """Get current population as shaders."""
    shaders = []
    
    for individual in current_population:
        dual_genome = individual['genome']
        
        # Compile dual CPPN to shader
        shader_code = compiler.compile_dual_to_glsl(
            dual_genome, engine.config, engine.time_config
        )
        
        # Count nodes and connections for both networks
        visual_nodes = len(dual_genome.visual.nodes)
        visual_conns = len([c for c in dual_genome.visual.connections.values() if c.enabled])
        time_nodes = len(dual_genome.time_signal.nodes)
        time_conns = len([c for c in dual_genome.time_signal.connections.values() if c.enabled])
        
        shaders.append({
            'id': individual['id'],
            'shader': shader_code,
            'clicks': individual['clicks'],
            'nodes': visual_nodes + time_nodes,
            'connections': visual_conns + time_conns,
            'visual_nodes': visual_nodes,
            'visual_connections': visual_conns,
            'time_nodes': time_nodes,
            'time_connections': time_conns
        })
    
    return jsonify({
        'generation': current_generation,
        'population': shaders
    })


@app.route('/api/click', methods=['POST'])
def record_click():
    """Record a click (fitness) for an individual."""
    data = request.json
    individual_id = data.get('id')
    
    for individual in current_population:
        if individual['id'] == individual_id:
            individual['clicks'] += 1
            individual['fitness'] = individual['clicks']
            # Update fitness on the dual genome
            individual['genome'].fitness = individual['clicks']
            return jsonify({
                'id': individual_id,
                'clicks': individual['clicks'],
                'status': 'recorded'
            })
    
    return jsonify({'error': 'Individual not found'}), 404


@app.route('/api/breed', methods=['POST'])
def breed():
    """Breed next generation from selected individuals."""
    global current_generation
    
    # Get individuals with clicks > 0
    parents = [ind for ind in current_population if ind['clicks'] > 0]
    
    if not parents:
        return jsonify({'error': 'No individuals selected'}), 400
    
    # Sort by clicks (fitness)
    parents.sort(key=lambda x: x['clicks'], reverse=True)
    
    # Take top parents (at least 2, at most 4)
    num_parents = min(max(2, len(parents)), 4)
    selected_parents = parents[:num_parents]
    
    # Breed new generation
    breed_next_generation(selected_parents)
    current_generation += 1
    
    return jsonify({
        'generation': current_generation,
        'parents_selected': num_parents,
        'parent_ids': [p['id'] for p in selected_parents],
        'parent_clicks': [p['clicks'] for p in selected_parents],
        'status': 'bred'
    })


@app.route('/api/save', methods=['POST'])
def save_individual():
    """Save a specific individual (dual genome)."""
    data = request.json
    individual_id = data.get('id')
    
    for individual in current_population:
        if individual['id'] == individual_id:
            os.makedirs('output/saved', exist_ok=True)
            
            dual_genome = individual['genome']
            
            # Save dual genome
            genome_path = f'output/saved/dual_genome_{individual_id}.pkl'
            engine.save_dual_genome(dual_genome, genome_path)
            
            # Save shader
            shader_code = compiler.compile_dual_to_glsl(
                dual_genome, engine.config, engine.time_config
            )
            shader_path = f'output/saved/pattern_{individual_id}.glsl'
            with open(shader_path, 'w') as f:
                f.write(shader_code)
            
            # Save shader bundle
            bundle_path = f'output/saved/pattern_{individual_id}_bundle.json'
            compiler.export_dual_shader_bundle(
                dual_genome, engine.config, engine.time_config, bundle_path
            )
            
            # Save image (using visual CPPN with linear time for static image)
            from PIL import Image
            img = engine.render_image(dual_genome.visual, resolution=512, time=0.5)
            img_path = f'output/saved/pattern_{individual_id}.png'
            Image.fromarray(img).save(img_path)
            
            return jsonify({
                'id': individual_id,
                'genome_path': genome_path,
                'shader_path': shader_path,
                'bundle_path': bundle_path,
                'image_path': img_path,
                'status': 'saved'
            })
    
    return jsonify({'error': 'Individual not found'}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get evolution statistics."""
    total_clicks = sum(ind['clicks'] for ind in current_population)
    selected_count = len([ind for ind in current_population if ind['clicks'] > 0])
    
    return jsonify({
        'generation': current_generation,
        'population_size': len(current_population),
        'total_clicks': total_clicks,
        'selected_count': selected_count,
        'genome_counter': genome_counter,
        'dual_cppn': True  # Flag to indicate dual-CPPN mode
    })


if __name__ == '__main__':
    print("=" * 60)
    print("EYECATCHER - Interactive Evolution Server")
    print("Dual-CPPN Mode: Visual + Time Signal Networks")
    print("=" * 60)
    print("\nStarting server...")
    print("Open http://localhost:5001 in your browser")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    # Initialize first population
    create_population()
    
    app.run(debug=True, port=5001)

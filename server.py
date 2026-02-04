"""
Interactive Evolution Server
Serves CPPN population and handles breeding
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from cppn_engine import CPPNEngine, create_random_genome
from shader_compiler import ShaderCompiler
import os
import pickle

app = Flask(__name__)
CORS(app)

# Global state
engine = CPPNEngine()
engine.create_population()
compiler = ShaderCompiler()

current_population = []
current_generation = 0
genome_counter = 0


def create_population(size=12):
    """Create initial random population."""
    global current_population, genome_counter
    current_population = []
    for i in range(size):
        genome = create_random_genome(engine.config, genome_id=genome_counter)
        genome_counter += 1
        current_population.append({
            'id': genome.key,
            'genome': genome,
            'fitness': 0,
            'clicks': 0
        })
    return current_population


def breed_next_generation(parents, population_size=12):
    """Breed new generation from selected parents."""
    global current_population, genome_counter
    
    new_population = []
    
    # Elitism: keep best parent
    best_parent = max(parents, key=lambda x: x['clicks'])
    new_population.append({
        'id': best_parent['genome'].key,
        'genome': best_parent['genome'],
        'fitness': 0,
        'clicks': 0
    })
    
    # Generate offspring
    while len(new_population) < population_size:
        if len(parents) == 1:
            # Only one parent: mutate
            child = engine.mutate_genome(parents[0]['genome'])
        else:
            # Multiple parents: 70% mutation, 30% crossover
            import random
            if random.random() < 0.7:
                parent = random.choice(parents)
                child = engine.mutate_genome(parent['genome'])
            else:
                p1, p2 = random.sample(parents, 2)
                child = engine.crossover_genomes(p1['genome'], p2['genome'])
        
        child.key = genome_counter
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
    data = request.json
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
        shader_code = compiler.compile_to_glsl(individual['genome'], engine.config)
        shaders.append({
            'id': individual['id'],
            'shader': shader_code,
            'clicks': individual['clicks'],
            'nodes': len(individual['genome'].nodes),
            'connections': len([c for c in individual['genome'].connections.values() if c.enabled])
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
    """Save a specific individual."""
    data = request.json
    individual_id = data.get('id')
    
    for individual in current_population:
        if individual['id'] == individual_id:
            os.makedirs('output/saved', exist_ok=True)
            
            # Save genome (with visualization)
            genome_path = f'output/saved/genome_{individual_id}.pkl'
            engine.save_genome(individual['genome'], genome_path, visualize=True)
            
            # Save shader
            shader_code = compiler.compile_to_glsl(individual['genome'], engine.config)
            shader_path = f'output/saved/pattern_{individual_id}.glsl'
            with open(shader_path, 'w') as f:
                f.write(shader_code)
            
            # Save image
            from PIL import Image
            img = engine.render_image(individual['genome'], resolution=512, time=0.5)
            img_path = f'output/saved/pattern_{individual_id}.png'
            Image.fromarray(img).save(img_path)
            
            # Check for network visualization
            network_path = f'output/saved/genome_{individual_id}_network.pdf'
            has_network = os.path.exists(network_path)
            
            return jsonify({
                'id': individual_id,
                'genome_path': genome_path,
                'shader_path': shader_path,
                'image_path': img_path,
                'network_path': network_path if has_network else None,
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
        'genome_counter': genome_counter
    })


if __name__ == '__main__':
    print("=" * 60)
    print("EYECATCHER - Interactive Evolution Server")
    print("=" * 60)
    print("\nStarting server...")
    print("Open http://localhost:5000 in your browser")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)
    
    # Initialize first population
    create_population()
    
    app.run(debug=True, port=5000)

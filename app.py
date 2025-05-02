from flask import Flask, render_template, request, jsonify
import networkx as nx

app = Flask(__name__)

class CPMScheduler:
    def __init__(self):
        self.tasks = {}
        self.dependencies = []
        self.graph = nx.DiGraph()
        
    def add_task(self, task_id, description, duration):
        """Ajoute une tâche au planificateur."""
        self.tasks[task_id] = {
            'description': description,
            'duration': duration,
            'early_start': 0,
            'early_finish': 0,
            'late_start': 0,
            'late_finish': 0,
            'slack': 0
        }
        self.graph.add_node(task_id, duration=duration)
        
    def add_dependency(self, predecessor, successor):
        """Ajoute une dépendance entre deux tâches."""
        if predecessor in self.tasks and successor in self.tasks:
            self.dependencies.append((predecessor, successor))
            self.graph.add_edge(predecessor, successor)
    
    def calculate_early_times(self):
        """Calcule les dates au plus tôt (forward pass)."""
        # Tri topologique pour s'assurer que tous les prédécesseurs sont traités avant
        for task in nx.topological_sort(self.graph):
            # Si aucun prédécesseur, early_start = 0
            predecessors = list(self.graph.predecessors(task))
            if not predecessors:
                self.tasks[task]['early_start'] = 0
            else:
                # early_start = max(early_finish des prédécesseurs)
                self.tasks[task]['early_start'] = max(
                    self.tasks[pred]['early_finish'] for pred in predecessors
                )
            
            # early_finish = early_start + durée
            self.tasks[task]['early_finish'] = (
                self.tasks[task]['early_start'] + self.tasks[task]['duration']
            )
    
    def calculate_late_times(self):
        """Calcule les dates au plus tard (backward pass)."""
        # Le projet se termine au plus tôt à la date de fin maximale
        project_end = max(task['early_finish'] for task in self.tasks.values())
        
        # Initialiser toutes les dates au plus tard à la fin du projet
        for task_id in self.tasks:
            self.tasks[task_id]['late_finish'] = project_end
        
        # Tri topologique inversé pour s'assurer que tous les successeurs sont traités avant
        for task in reversed(list(nx.topological_sort(self.graph))):
            successors = list(self.graph.successors(task))
            if not successors:
                # Si aucun successeur, late_finish = fin du projet
                self.tasks[task]['late_finish'] = project_end
            else:
                # late_finish = min(late_start des successeurs)
                self.tasks[task]['late_finish'] = min(
                    self.tasks[succ]['late_start'] for succ in successors
                )
            
            # late_start = late_finish - durée
            self.tasks[task]['late_start'] = (
                self.tasks[task]['late_finish'] - self.tasks[task]['duration']
            )
    
    def calculate_slack(self):
        """Calcule la marge pour chaque tâche."""
        for task_id in self.tasks:
            self.tasks[task_id]['slack'] = (
                self.tasks[task_id]['late_start'] - self.tasks[task_id]['early_start']
            )
    
    def find_critical_path(self):
        """Identifie le chemin critique (tâches avec marge nulle)."""
        critical_tasks = [
            task_id for task_id, task in self.tasks.items() if task['slack'] == 0
        ]
        
        # Construire le chemin critique en ordre
        critical_path = []
        visited = set()
        
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            
            successors = list(self.graph.successors(node))
            critical_successors = [
                succ for succ in successors 
                if succ in critical_tasks
            ]
            
            for succ in critical_successors:
                dfs(succ)
                
            if node in critical_tasks:
                critical_path.append(node)
        
        # Trouver les tâches de départ (sans prédécesseurs)
        start_tasks = [
            task for task in critical_tasks 
            if not list(self.graph.predecessors(task))
        ]
        
        for task in start_tasks:
            dfs(task)
            
        return critical_path
    
    def schedule(self):
        """Effectuer l'ordonnancement complet."""
        self.calculate_early_times()
        self.calculate_late_times()
        self.calculate_slack()
        critical_path = self.find_critical_path()
        
        project_duration = max(task['early_finish'] for task in self.tasks.values())
        
        return {
            'tasks': self.tasks,
            'critical_path': critical_path,
            'project_duration': project_duration
        }

# Routes Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    scheduler = CPMScheduler()
    
    # Ajouter les tâches
    for task in data['tasks']:
        scheduler.add_task(
            task['id'], 
            task['description'], 
            task['duration']
        )
    
    # Ajouter les dépendances
    for dep in data['dependencies']:
        scheduler.add_dependency(dep['from'], dep['to'])
    
    # Calculer l'ordonnancement
    result = scheduler.schedule()
    
    return jsonify(result)  

if __name__ == '__main__':
    app.run(debug=True)
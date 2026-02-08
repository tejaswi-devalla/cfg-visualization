import streamlit as st
import ast
import networkx as nx
import graphviz

# --- Backend: CFG Builder ---
class CFGBuilder(ast.NodeVisitor):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.counter = 0
        self.last_node = None

    def new_node(self, label, shape="box"):
        self.counter += 1
        node_id = f"node_{self.counter}"
        # Using Courier font to make the code look like an editor
        self.graph.add_node(node_id, label=label, shape=shape, fontname="Courier New")
        return node_id

    def add_edge(self, source, target, label=""):
        self.graph.add_edge(source, target, label=label)

    def build(self, code):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return None, f"Syntax Error: {e}"
        
        start_node = self.new_node("START", shape="oval")
        self.last_node = start_node
        
        for node in tree.body:
            self.visit(node)
            
        end_node = self.new_node("STOP", shape="oval")
        if self.last_node:
            self.add_edge(self.last_node, end_node)
            
        return self.graph, None

    def visit_Assign(self, node):
        # Extracts actual code like 'x = 10'
        label = ast.unparse(node)
        current_node = self.new_node(label)
        if self.last_node:
            self.add_edge(self.last_node, current_node)
        self.last_node = current_node

    def visit_Expr(self, node):
        # Extracts code like 'print(x)'
        label = ast.unparse(node)
        current_node = self.new_node(label)
        if self.last_node:
            self.add_edge(self.last_node, current_node)
        self.last_node = current_node

    def visit_If(self, node):
        # Create decision diamond with the if-condition text
        label = f"if {ast.unparse(node.test)}:"
        condition_node = self.new_node(label, shape="diamond")
        if self.last_node:
            self.add_edge(self.last_node, condition_node)
        
        # --- True Branch ---
        self.last_node = condition_node
        for child in node.body:
            self.visit(child)
        end_true = self.last_node
        
        # --- False Branch (Else) ---
        self.last_node = condition_node 
        if node.orelse:
            for child in node.orelse:
                self.visit(child)
        else:
            # If there's no else, the False path goes straight to merge
            pass
        end_false = self.last_node
        
        # Merge Point
        merge_node = self.new_node("merge", shape="point")
        self.add_edge(end_true, merge_node, label="True")
        self.add_edge(end_false, merge_node, label="False")
        self.last_node = merge_node

    def visit_While(self, node):
        # Create decision diamond with while-condition text
        label = f"while {ast.unparse(node.test)}:"
        condition_node = self.new_node(label, shape="diamond")
        if self.last_node:
            self.add_edge(self.last_node, condition_node)
        
        # --- Loop Body ---
        self.last_node = condition_node
        for child in node.body:
            self.visit(child)
        
        # Loop Back Edge
        self.add_edge(self.last_node, condition_node, label="Loop Back")
        
        # Loop Exit Path
        exit_node = self.new_node("exit_loop", shape="point")
        self.add_edge(condition_node, exit_node, label="False")
        self.last_node = exit_node

# --- Metrics Calculation ---
def calculate_metrics(graph):
    if not graph:
        return {}
    
    n = graph.number_of_nodes()
    e = graph.number_of_edges()
    
    # Predicate nodes = nodes where a decision is made
    predicate_nodes = [n for n in graph.nodes() if graph.out_degree(n) > 1]
    p = len(predicate_nodes)
    
    # Cyclomatic Complexity V(G) = E - N + 2
    complexity = e - n + 2
    
    return {
        "nodes": n,
        "edges": e,
        "predicates": p,
        "complexity": complexity
    }

# --- Streamlit UI Layout ---
st.set_page_config(page_title="CFG Pro Analyzer", layout="wide")

st.title("🛡️ Program CFG Visualizer & Metrics")
st.info("The graph and metrics update in real-time as you type.")

col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Source Code Editor")
    code_input = st.text_area(
        "Python Code:", 
        height=450, 
        value="""x = 10\nif x > 5:\n    print("Large")\nelse:\n    x = 0\n\nwhile x < 5:\n    x = x + 1\nprint("Done")"""
    )

with col2:
    st.subheader("CFG Visualization")
    builder = CFGBuilder()
    graph, error = builder.build(code_input)

    if error:
        st.error(error)
    elif graph:
        # 1. Show Metrics
        m = calculate_metrics(graph)
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Nodes", m["nodes"])
        m_col2.metric("Edges", m["edges"])
        m_col3.metric("Predicates", m["predicates"])
        m_col4.metric("Regions", m["complexity"])

        # 2. Render Graph
        dot = graphviz.Digraph()
        dot.attr(rankdir='TB') # Top to Bottom flow
        
        for node, data in graph.nodes(data=True):
            dot.node(node, label=data.get('label', ''), shape=data.get('shape', 'box'), fontname=data.get('fontname'))
        
        for u, v, data in graph.edges(data=True):
            dot.edge(u, v, label=data.get('label', ''))
            
        st.graphviz_chart(dot)
#!/usr/bin/env python3
"""
Comprehensive Synthetic Academic Dataset Generator for Chanakya Research Commons.
Course: V Sem B.Tech Data Mining and Warehousing, Chanakya University, Bangalore.

Mandatory Requirements & Scale Targets:
1. Members & Departments:
   - >= 50 university members across >= 6 departments (Students, Faculty, Researchers, Admins).
   - Department-aligned research interests, realistic profile info, and activity patterns.
2. Posts & Comments:
   - >= 2,000 minimum combined; larger project target: 5,000+ posts and 15,000+ comments (20,000+ combined).
   - Meaningful research discussions, questions, paper recommendations, and threaded academic conversations.
3. Save, View & Search Events:
   - >= 10,000 minimum combined over >= 6 months; larger project targets:
     * 10,000+ paper-save relationships (library_saves)
     * 20,000+ views (activity_events with event_type='view_paper')
     * 10,000+ searches (activity_events with event_type='search' & search_history)
     * 50,000+ total activity events (activity_events)
4. Follow Relationships:
   - Academic networking patterns (students following faculty advisors, researchers following shared interests).
5. Realistic Activity Patterns:
   - Diurnal and weekly rhythms (weekday peaks, exam lulls, conference sprints).
   - Department-correlated saves and searches, cross-department collaborations.
   - Planted ground truth: duplicates, author variations, spam accounts, and QML topic spike.
6. Documented & Reproducible:
   - Fixed random seed: 42.
   - Clean reset-and-regenerate support.

Usage:
    python scripts/generate_synthetic_data.py [--reset]
"""

import os
import sys
import json
import random
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.db import query_db, get_connection
from mining.embeddings import generate_embeddings_batch

SEED = 42
random.seed(SEED)

SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)

# 1. Academic Domains & Topics
TOPICS_DATA = [
    {"name": "Deep Learning & Neural Architectures", "slug": "deep-learning", "domain": "Artificial Intelligence", "desc": "Foundational deep neural networks, transformers, and representation learning."},
    {"name": "Natural Language Processing & LLMs", "slug": "nlp-llms", "domain": "Artificial Intelligence", "desc": "Large language models, semantic parsing, retrieval-augmented generation, and tokenization."},
    {"name": "Data Mining & Knowledge Discovery", "slug": "data-mining", "domain": "Computer Science", "desc": "Frequent itemset mining, graph analytics, association rules, and anomaly detection."},
    {"name": "Distributed Cloud Systems", "slug": "distributed-systems", "domain": "Computer Science", "desc": "Microservices, consensus algorithms, high-throughput streaming, and fault tolerance."},
    {"name": "Computer Vision & Visual Computing", "slug": "computer-vision", "domain": "Artificial Intelligence", "desc": "Object detection, segmentation, multimodal models, and 3D reconstruction."},
    {"name": "Wireless IoT & Edge Computing", "slug": "iot-edge-computing", "domain": "Information Technology", "desc": "Edge AI, low-power sensor networks, 6G communication, and smart campus IoT."},
    {"name": "VLSI Design & Neuromorphic Hardware", "slug": "vlsi-neuromorphic", "domain": "Electronics", "desc": "Energy-efficient compute-in-memory, ASIC architectures, and neuromorphic accelerators."},
    {"name": "Bioinformatics & Genomic Analytics", "slug": "bioinformatics", "domain": "Biotechnology", "desc": "DNA sequence alignment, protein folding prediction, and biomedical data mining."},
    {"name": "Decision Science & Operations Analytics", "slug": "decision-analytics", "domain": "Management", "desc": "Stochastic optimization, supply chain resilience, econometric forecasting, and game theory."},
    {"name": "Quantum Machine Learning", "slug": "quantum-ml", "domain": "Multidisciplinary", "desc": "Variational quantum circuits, quantum kernels, and hybrid quantum-classical algorithms."}
]

# Department code to primary topic alignment
DEPT_TOPIC_MAP = {
    "CSE": ["Data Mining & Knowledge Discovery", "Distributed Cloud Systems", "Deep Learning & Neural Architectures", "Quantum Machine Learning"],
    "DSAI": ["Deep Learning & Neural Architectures", "Natural Language Processing & LLMs", "Computer Vision & Visual Computing", "Data Mining & Knowledge Discovery"],
    "ECE": ["VLSI Design & Neuromorphic Hardware", "Wireless IoT & Edge Computing", "Computer Vision & Visual Computing"],
    "ISE": ["Distributed Cloud Systems", "Wireless IoT & Edge Computing", "Data Mining & Knowledge Discovery"],
    "BTBI": ["Bioinformatics & Genomic Analytics", "Deep Learning & Neural Architectures"],
    "MDS": ["Decision Science & Operations Analytics", "Data Mining & Knowledge Discovery"]
}

# Title generation templates per topic
TITLE_TEMPLATES = {
    "Deep Learning & Neural Architectures": [
        "Attention Mechanisms for Efficient Vision Transformers",
        "Self-Supervised Representation Learning on Sparse Datasets",
        "Gradient Regularization and Generalization in Deep ResNets",
        "Adaptive Activation Functions for Deep Convolutional Networks",
        "Parameter-Efficient Fine-Tuning of Foundation Models",
        "Adversarial Robustness and Certified Bounds in Neural Networks",
        "Normalized Weight Initialization for Ultra-Deep Networks",
        "Neural Architecture Search Using Reinforcement Learning"
    ],
    "Natural Language Processing & LLMs": [
        "Retrieval-Augmented Generation with Dynamic Passage Re-Ranking",
        "Instruction Tuning and Alignment for Domain-Specific LLMs",
        "Efficient Context Window Extension via Rotary Position Embeddings",
        "Cross-Lingual Semantic Representation in Low-Resource Indian Languages",
        "Hallucination Mitigation in Large Language Models via Fact Verification",
        "Contrastive Learning for Scientific Abstract Summarization",
        "Token-Free Language Modeling Using Character Encodings",
        "Prompt Optimization and Chain-of-Thought Reasoning in Code Models"
    ],
    "Data Mining & Knowledge Discovery": [
        "High-Utility Frequent Itemset Mining on Stream Data",
        "Scalable Association Rule Mining with Parallel FP-Growth",
        "Graph Neural Networks for Node Classification in Academic Networks",
        "Outlier and Anomaly Detection in Multidimensional Sensor Logs",
        "Dimensionality Reduction via Variational Autoencoders and UMAP",
        "Temporal Pattern Discovery in Medical Electronic Health Records",
        "Clustering Non-Convex Clusters with Density-Based Graph Traversal",
        "Privacy-Preserving Association Rule Discovery over Federated Datasets"
    ],
    "Distributed Cloud Systems": [
        "Consensus Under Partial Synchrony in Geographically Distributed Systems",
        "Predictive Auto-Scaling for Cloud Microservices Using LSTM",
        "Zero-Copy Memory Transport in High-Throughput Stream Processing",
        "Fault-Tolerant Distributed Storage with Erasure Coding",
        "Serverless Workflow Orchestration with Minimal Cold-Start Latency",
        "Consensus-Driven Decentralized Identity Systems",
        "Energy-Aware Task Scheduling in Heterogeneous Cloud Clusters",
        "Load Balancing Across Hybrid Multi-Cloud Academic Environments"
    ],
    "Computer Vision & Visual Computing": [
        "Real-Time Object Detection on Edge Embedded Platforms",
        "Zero-Shot Multi-Modal Visual Question Answering",
        "Self-Attention Diffusion Models for High-Fidelity Medical Imaging",
        "Weakly Supervised Semantic Segmentation Using Class Activation Maps",
        "End-to-End Autonomous Driving Perception Using Occupancy Grids",
        "Depth Estimation from Monocular Images Using Transformer Backbones",
        "Robust Feature Matching Under Severe Illumination Variations",
        "Video Action Recognition with Spatio-Temporal Graph Networks"
    ],
    "Wireless IoT & Edge Computing": [
        "Decentralized Federated Learning for Smart Campus IoT Networks",
        "Energy Harvesting Protocols for Ultra-Low Power Sensor Nodes",
        "Channel Estimation and Beamforming for Sub-THz 6G Networks",
        "Intrusion Detection in Industrial IoT Using Ensemble Tree Models",
        "Lightweight Cryptographic Protocols for Microcontroller Networks",
        "Edge-Cloud Collaborative Inference for Autonomous Drone Fleets",
        "Delay-Tolerant Routing in Mobile Opportunistic Sensor Networks",
        "Real-Time Air Quality Monitoring Using LoRaWAN Sensor Meshes"
    ],
    "VLSI Design & Neuromorphic Hardware": [
        "Compute-in-Memory Architecture Using Resistive RAM Arrays",
        "Low-Power Spiking Neural Network Processors for Event Cameras",
        "Sub-Threshold CMOS Design for Wearable Health Monitoring Devices",
        "High-Speed Radix-4 Multipliers for Cryptographic Hardware Engines",
        "Thermal-Aware Floorplanning for 3D Integrated Circuit Stacks",
        "Fault-Tolerant NoC Routers with Dynamic Virtual Channel Allocation",
        "Hardware-Accelerated Homomorphic Encryption Coprocessors",
        "Analog Front-End Design for High-Precision Neural Interfaces"
    ],
    "Bioinformatics & Genomic Analytics": [
        "Graph-Based Pangenome Alignment and Structural Variant Calling",
        "Deep Learning for Alternative Splicing Prediction from RNA-Seq",
        "Molecular Dynamics Simulations of Drug-Target Binding Affinities",
        "Metagenomic Species Abundance Estimation via K-mer Counting",
        "Single-Cell Transcriptomics Clustering and Trajectory Inference",
        "Protein-Protein Interaction Network Mining Using Node2Vec",
        "CRISPR-Cas9 Off-Target Cleavage Prediction Using Convolutional Models",
        "Genome-Wide Association Study of Metabolic Biomarkers in Populations"
    ],
    "Decision Science & Operations Analytics": [
        "Dynamic Pricing and Inventory Optimization Under Stochastic Demand",
        "Robust Supply Chain Network Design with Disruptions and Tariffs",
        "Multi-Objective Portfolio Optimization Using Genetic Algorithms",
        "Stochastic Facility Location and Vehicle Routing in Smart Logistics",
        "Game-Theoretic Resource Allocation in Carbon Offset Markets",
        "Markov Decision Processes for Patient Admission in Hospital ICUs",
        "Predictive Maintenance Scheduling Using Survival Analysis Models",
        "Simulating Consumer Behavioral Shifts During Macroeconomic Shocks"
    ],
    "Quantum Machine Learning": [
        "Variational Quantum Classifiers for High-Dimensional Particle Physics",
        "Barren Plateaus Mitigation in Quantum Neural Network Training",
        "Quantum Support Vector Machines with Enhanced Feature Mappings",
        "Fault-Tolerant Quantum Fourier Transform for Financial Modeling",
        "Quantum Approximate Optimization Algorithm for Maximum Cut Problems",
        "Hybrid Classical-Quantum Convolutional Architectures for Vision",
        "Quantum Error Mitigation Techniques in Noisy Intermediate-Scale Quantum Hardware",
        "Tensor Network Simulations of Quantum Many-Body Dynamics"
    ]
}

JOURNALS = [
    "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "ACM Computing Surveys",
    "Nature Machine Intelligence",
    "Journal of Machine Learning Research",
    "IEEE Transactions on Knowledge and Data Engineering",
    "Bioinformatics (Oxford Academic)",
    "VLSI Design and Test Symposium (VDAT)",
    "Operations Research and Management Science",
    "Physical Review Research",
    "IEEE Internet of Things Journal"
]

AUTHOR_POOL = [
    ("Anand Sharma", "A. Sharma", "Department of Computer Science & Engineering"),
    ("Priya Venkatesh", "P. Venkatesh", "Department of Data Science & Artificial Intelligence"),
    ("Rajesh Kumar", "R. Kumar", "Department of Computer Science & Engineering"),
    ("Sunita Rao", "S. Rao", "Department of Information Science & Engineering"),
    ("Karthik Narayanan", "K. Narayanan", "Department of Electronics & Communication Engineering"),
    ("Arunachalam Murthy", "A. Murthy", "Department of Biotechnology & Bioinformatics"),
    ("Deepa Chandrasekhar", "D. Chandrasekhar", "Department of Management & Decision Sciences"),
    ("Vikram Deshmukh", "V. Deshmukh", "Department of Data Science & Artificial Intelligence"),
    ("Meenakshi Sundaram", "M. Sundaram", "Department of Computer Science & Engineering"),
    ("Girish Hegde", "G. Hegde", "Department of Electronics & Communication Engineering"),
    ("Ananya Banerjee", "A. Banerjee", "Department of Biotechnology & Bioinformatics"),
    ("Rohan Kulkarni", "R. Kulkarni", "Department of Information Science & Engineering"),
    ("Sneha Patil", "S. Patil", "Department of Data Science & Artificial Intelligence"),
    ("Manoj Nambiar", "M. Nambiar", "Department of Management & Decision Sciences"),
    ("Divya Raghavan", "D. Raghavan", "Department of Computer Science & Engineering")
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Akhil", "Akshara", "Amrita", "Arjun", "Bhavya", "Chetan", "Chinmay", "Darshan",
    "Devika", "Esha", "Gaurav", "Harini", "Hemanth", "Isha", "Jayant", "Jyoti", "Kavya", "Keerthi",
    "Madhav", "Manish", "Naveen", "Neha", "Nikhil", "Pallavi", "Pooja", "Pranav", "Prathik", "Rakesh",
    "Reshma", "Ritu", "Rohit", "Sameer", "Sanjay", "Sanjana", "Shreya", "Siddharth", "Sindhu", "Srinivas",
    "Swati", "Tarun", "Varun", "Veda", "Vidya", "Vijaya", "Vinay", "Yamini", "Yashwant", "Zoya",
    "Abhishek", "Anandita", "Bhargav", "Deepak", "Kalyani", "Maitreyi", "Prashant", "Revathi", "Sujata", "Tanvi"
]
LAST_NAMES = [
    "Bhat", "Deshpande", "Gowda", "Iyer", "Joshi", "Kamat", "Menon", "Nair", "Patel",
    "Prabhu", "Rao", "Reddy", "Sharma", "Shetty", "Singh", "Soni", "Upadhyay", "Verma"
]

# Rich discussion post prompt templates
POST_TEMPLATES = [
    (
        "Empirical Scalability and Complexity Bounds in {topic}",
        "Colleagues, we recently conducted systematic scalability benchmarks on {topic}. "
        "Under increasing data scale, we observed that while algorithmic accuracy remains competitive, "
        "memory allocation exhibits quadratic overhead during peak phases. "
        "Has anyone in the department evaluated memory-efficient pruning or batching strategies to mitigate this?",
        ["scalability", "complexity", "benchmarks"]
    ),
    (
        "Open Methodological Challenge: Variance in {topic} Baselines",
        "In our recent lab replication experiments for {topic}, published baseline figures showed up to 14% discrepancy "
        "depending on initialization seeds and normalization protocols. "
        "We are organizing a university-wide reading group to synthesize standard replication protocols. "
        "Key questions include stochastic variance, hyperparameter stability, and cross-dataset generalizability.",
        ["reproducibility", "evaluation", "methodology"]
    ),
    (
        "Integration Challenges: Deploying {topic} on Edge Hardware",
        "Our team is exploring real-world hardware deployment for models trained in {topic}. "
        "Targeting edge devices with strict power (<5W) and memory constraints (<4GB) reveals non-trivial bottlenecks. "
        "We welcome suggestions on integer quantization, layer fusion, and kernel-level optimizations suitable for our campus testbed.",
        ["hardware", "edge-computing", "optimization"]
    ),
    (
        "Theoretical Guarantees vs Empirical Reality in {topic}",
        "While theoretical asymptotic bounds for {topic} guarantee rapid convergence under convexity assumptions, "
        "empirical loss surfaces encountered in practice display significant non-convex saddle points. "
        "Let us discuss potential regularizers or modified loss formulations that maintain theoretical stability without hurting empirical performance.",
        ["theory", "convergence", "algorithms"]
    ),
    (
        "Dataset Quality and Noise Mitigation Strategies in {topic}",
        "High-fidelity training data remains a critical bottleneck for state-of-the-art advances in {topic}. "
        "We are analyzing the impact of synthetic label noise versus human annotation errors. "
        "What data-cleansing pipelines or self-supervised filtering methods have proven most resilient in your department projects?",
        ["dataset", "data-quality", "preprocessing"]
    ),
    (
        "Cross-Disciplinary Perspectives: Applying {topic} to Real-World Problems",
        "Emerging synergies between {topic} and applied computational domains present exciting research avenues. "
        "By reformulating the core objective function, we can directly adapt existing mathematical frameworks to domain-specific constraints. "
        "Looking for faculty and researcher collaborators across departments interested in joint grant proposals.",
        ["collaboration", "interdisciplinary", "applied-research"]
    ),
    (
        "Comparative Analysis of State-of-the-Art Architectures in {topic}",
        "Following the latest 2026 conference proceedings, multiple competing architectures have emerged for {topic}. "
        "We compiled a side-by-side comparison of parameter counts, inference latency, and qualitative error modes. "
        "Please review the attached paper reference and share your thoughts on the most promising long-term direction.",
        ["literature-review", "architectures", "sota"]
    ),
    (
        "Replication Study and Negative Results in {topic}",
        "In the spirit of open scientific inquiry, we are sharing preliminary negative results from our {topic} experiments. "
        "Contrary to widely cited claims, scaling model capacity without structural inductive biases failed to resolve the tail distribution failure modes. "
        "Detailed logs and reproduction notebooks are linked for peer review.",
        ["replication", "negative-results", "open-science"]
    )
]

# Rich academic comment templates
COMMENT_TEMPLATES = [
    "We observed very similar behavior in our laboratory simulations. Normalizing input distributions reduced the variance significantly.",
    "Great point. Have you verified whether the asymptotic bounds hold when the batch size exceeds standard thresholds?",
    "I recommend reviewing Theorem 3 in the attached paper regarding algorithmic convergence guarantees under noisy gradients.",
    "From our testing, 8-bit integer quantization preserved 99.2% of full-precision accuracy while reducing RAM consumption by 3.8x.",
    "This aligns closely with our Department seminar findings last month. We should definitely coordinate on a joint follow-up paper.",
    "Did your benchmarks account for cache thrashing? We encountered identical latency spikes before restructuring memory layouts.",
    "An excellent initiative. I would like to contribute our departmental dataset to validate cross-domain generalization.",
    "In our experience, applying adaptive learning rate decay with cosine annealing resolved the saddle point stalling you described.",
    "Have you tested this against the standard IEEE/ACM benchmark corpora? Baseline comparability would strengthen the submission.",
    "Very thoughtful analysis. We noticed that increasing regularization strength mitigates the tail distribution issue effectively."
]

THREAD_REPLIES = [
    "Thanks for the suggestion! We implemented your recommended normalization and observed an immediate 4.2% stability gain.",
    "That is a great observation. We are currently rerunning the benchmarks on the expanded test suite to verify your hypothesis.",
    "Agreed. In fact, Section 4 of the reference paper discusses exactly that trade-off in detail.",
    "Good catch on the memory layout. Restructuring into contiguous blocks indeed shaved 18ms off the median inference time.",
    "Let us schedule a brief discussion after Thursday's faculty colloquium to review the experimental logs together."
]

SEARCH_QUERIES_BY_TOPIC = {
    "Deep Learning & Neural Architectures": [
        "vision transformer attention mechanism", "parameter efficient fine tuning peft", "self supervised representation learning",
        "deep resnet gradient regularization", "neural architecture search reinforcement learning", "adversarial robustness neural networks"
    ],
    "Natural Language Processing & LLMs": [
        "retrieval augmented generation dynamic reranking", "domain specific llm instruction tuning", "rotary position embeddings context extension",
        "hallucination mitigation fact verification", "scientific abstract contrastive summarization", "chain of thought reasoning prompt"
    ],
    "Data Mining & Knowledge Discovery": [
        "frequent itemset mining fp growth algorithm", "scalable association rules parallel mining", "graph neural networks academic citations",
        "anomaly detection time series sensor logs", "density based spatial clustering dbscan", "federated privacy preserving association rules"
    ],
    "Distributed Cloud Systems": [
        "distributed consensus raft paxos synchrony", "predictive autoscaling cloud microservices", "serverless cold start latency reduction",
        "fault tolerant storage erasure coding", "zero copy stream processing memory", "heterogeneous cloud task scheduling energy"
    ],
    "Computer Vision & Visual Computing": [
        "real time object detection embedded yolo", "zero shot multimodal visual question answering", "diffusion models medical imaging",
        "weakly supervised semantic segmentation cam", "monocular depth estimation transformer", "video action recognition spatiotemporal"
    ],
    "Wireless IoT & Edge Computing": [
        "decentralized federated edge learning iot", "lorawan smart campus air quality mesh", "energy harvesting ultra low power sensor",
        "sub thz 6g beamforming channel estimation", "industrial iot intrusion detection tree", "autonomous drone fleet collaborative inference"
    ],
    "VLSI Design & Neuromorphic Hardware": [
        "compute in memory resistive ram rram", "spiking neural network neuromorphic processor", "sub threshold cmos wearable biomedical",
        "radix 4 cryptographic hardware multiplier", "3d ic thermal aware floorplanning", "homomorphic encryption hardware accelerator"
    ],
    "Bioinformatics & Genomic Analytics": [
        "graph pangenome alignment structural variants", "deep learning rna seq alternative splicing", "molecular dynamics drug target binding",
        "metagenomic species k mer abundance", "single cell transcriptomics clustering trajectory", "crispr cas9 off target cleavage prediction"
    ],
    "Decision Science & Operations Analytics": [
        "dynamic pricing stochastic inventory optimization", "robust supply chain network design disruptions", "multi objective portfolio genetic algorithm",
        "stochastic facility location vehicle routing", "markov decision process icu patient admission", "predictive maintenance survival analysis"
    ],
    "Quantum Machine Learning": [
        "variational quantum classifier particle physics", "quantum support vector machines kernel mapping", "barren plateaus quantum neural network training",
        "quantum approximate optimization algorithm qaoa", "hybrid quantum classical convolutional networks", "quantum error mitigation nisq hardware"
    ]
}


def clean_title_str(t):
    return re.sub(r"[^\w\s]", "", t).lower().strip()


def generate_dataset(reset=False):
    print("=" * 70)
    print("CHANAKYA RESEARCH COMMONS — SYNTHETIC ACTIVITY DATASET GENERATOR")
    print(f"Random Seed: {SEED} (Fully Reproducible) | Mode: {'Reset & Regenerate' if reset else 'Standard'}")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()

    if reset:
        print("Resetting dynamic user and activity tables...")
        # Clear child tables first to respect foreign keys
        cur.execute("DELETE FROM activity_events;")
        cur.execute("DELETE FROM search_history;")
        cur.execute("DELETE FROM post_votes;")
        cur.execute("DELETE FROM post_comments;")
        cur.execute("DELETE FROM post_tags;")
        cur.execute("DELETE FROM posts;")
        cur.execute("DELETE FROM library_saves;")
        cur.execute("DELETE FROM collections;")
        cur.execute("DELETE FROM user_followers;")
        cur.execute("DELETE FROM user_interests;")
        cur.execute("DELETE FROM topic_followers;")
        cur.execute("DELETE FROM paper_sources;")
        cur.execute("DELETE FROM paper_authors;")
        cur.execute("DELETE FROM papers;")
        cur.execute("DELETE FROM users;")
        cur.execute("DELETE FROM topics;")
        try:
            cur.execute("DELETE FROM sqlite_sequence;")
        except Exception:
            pass
        conn.commit()
        print("Database cleared.")

    # 1. Fetch departments
    cur.execute("SELECT id, code, name FROM departments")
    depts = [dict(r) for r in cur.fetchall()]
    dept_map = {d["code"]: d["id"] for d in depts}
    dept_ids = [d["id"] for d in depts]
    print(f"Loaded {len(depts)} university departments: {list(dept_map.keys())}")

    # 2. Seed Topics
    print("Seeding Academic Topics...")
    topic_ids = {}
    for td in TOPICS_DATA:
        cur.execute("SELECT id FROM topics WHERE slug = ?", (td["slug"],))
        row = cur.fetchone()
        if row:
            t_id = row[0]
        else:
            cur.execute(
                "INSERT INTO topics (name, slug, domain, description) VALUES (?, ?, ?, ?)",
                (td["name"], td["slug"], td["domain"], td["desc"])
            )
            t_id = cur.lastrowid
        topic_ids[td["name"]] = t_id
    conn.commit()

    # 3. Create 60 Members (55 Legitimate + 5 Planted Spam Bots)
    print("Generating 60 University Members across 6 Departments...")
    users = []
    ground_truth_spam_users = []

    # 55 Legitimate University Members
    # Roles distribution: 27 Students, 14 Researchers, 11 Faculty, 3 Admins
    roles = ["Student"] * 27 + ["Researcher"] * 14 + ["Faculty"] * 11 + ["Admin"] * 3
    random.shuffle(roles)

    dept_code_list = list(dept_map.keys())
    user_insert_rows = []

    for i in range(55):
        fn = FIRST_NAMES[i % len(FIRST_NAMES)]
        ln = LAST_NAMES[(i * 3 + 1) % len(LAST_NAMES)]
        username = f"{fn.lower()}.{ln.lower()}{i+1}"
        email = f"{username}@chanakya.ac.in"
        full_name = f"{fn} {ln}"
        role = roles[i]
        dept_code = dept_code_list[i % len(dept_code_list)]
        dept_id = dept_map[dept_code]
        bio = f"{role} at Chanakya University, {depts[i % len(depts)]['name']}. Specializing in academic research, empirical evaluation, and advanced data technologies."
        scholar = f"https://scholar.google.com/citations?user={username}"
        website = f"https://chanakya.ac.in/faculty/{username}" if role in ("Faculty", "Researcher") else ""

        # Check existing
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing = cur.fetchone()
        if existing:
            u_id = existing[0]
        else:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, role, department_id, bio, website_url, scholar_url, is_spam_flagged)
                VALUES (?, ?, 'pbkdf2:sha256:600000$dummy$hash', ?, ?, ?, ?, ?, ?, 0)
                """,
                (username, email, full_name, role, dept_id, bio, website, scholar)
            )
            u_id = cur.lastrowid
        users.append({
            "id": u_id, "username": username, "full_name": full_name,
            "role": role, "dept_id": dept_id, "dept_code": dept_code, "is_spam": False
        })

    # 5 Planted Spam Bot Accounts
    spam_templates = [
        ("bot_promo_99", "promo99@gmail.com", "Free Crypto Research Hub", "Student"),
        ("paper_mill_agent", "sellpapers@fastboost.org", "Buy Scopus Paper Fast", "Student"),
        ("ad_spammer_x", "winprizes@clickad.net", "Scholarship Cash Giveaways", "Student"),
        ("spam_bot_academic", "rankbooster@citationhack.biz", "Instant Citations Service", "Researcher"),
        ("fake_profile_bot", "boostyourprofile@fastindex.cc", "Automated Profile Booster", "Student")
    ]
    for username, email, full_name, role in spam_templates:
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing = cur.fetchone()
        if existing:
            u_id = existing[0]
        else:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, role, department_id, bio, website_url, scholar_url, is_spam_flagged)
                VALUES (?, ?, 'pbkdf2:sha256:600000$dummy$hash', ?, ?, ?, 'Commercial promotional account. Automated activity.', 'http://spam-link.org', '', 1)
                """,
                (username, email, full_name, role, dept_ids[0])
            )
            u_id = cur.lastrowid
        users.append({
            "id": u_id, "username": username, "full_name": full_name,
            "role": role, "dept_id": dept_ids[0], "dept_code": "CSE", "is_spam": True
        })
        ground_truth_spam_users.append({
            "user_id": u_id, "username": username, "reason": "Bursty spam posting & commercial promotional text"
        })

    conn.commit()

    # Assign Department-Correlated Research Interests
    print("Assigning Department-Correlated Research Interests...")
    user_interest_rows = []
    for u in users:
        if not u["is_spam"]:
            # Pick 2-3 primary interests from department topic mapping
            dept_primary_topics = DEPT_TOPIC_MAP.get(u["dept_code"], list(topic_ids.keys()))
            selected_topics = random.sample(dept_primary_topics, k=min(len(dept_primary_topics), random.randint(2, 3)))
            # Add 1 cross-disciplinary topic with 50% probability
            all_other_topics = [t for t in topic_ids.keys() if t not in selected_topics]
            if random.random() < 0.5:
                selected_topics.append(random.choice(all_other_topics))

            for t_name in selected_topics:
                user_interest_rows.append((u["id"], t_name, round(random.uniform(0.75, 1.0), 2)))

    cur.executemany("INSERT OR IGNORE INTO user_interests (user_id, topic_name, weight) VALUES (?, ?, ?)", user_interest_rows)
    conn.commit()

    # 4. Generate 520 Research Papers (480 Original + 40 Planted Duplicates)
    print("Generating 520 Research Papers & Planted Duplicates...")
    papers_inserted = []
    ground_truth_duplicates = []
    ground_truth_author_resolution = []

    topic_name_list = list(topic_ids.keys())
    texts_for_embedding = []
    paper_records_to_insert = []

    # 480 Base Original Papers
    for i in range(480):
        topic_name = topic_name_list[i % len(topic_name_list)]
        t_id = topic_ids[topic_name]
        templates = TITLE_TEMPLATES[topic_name]
        base_title = templates[i % len(templates)]
        variant_suffix = f" — Phase {i//len(templates) + 1}: Experimental Analysis and Benchmarking" if i >= len(templates) else ""
        title = f"{base_title}{variant_suffix}"
        clean_title = clean_title_str(title)
        year = random.randint(2019, 2026)
        venue = random.choice(JOURNALS)
        citations = int(random.expovariate(1/18)) + random.randint(0, 15)
        doi = f"10.1145/chanakya.{year}.{1000 + i}"
        arxiv_id = f"{str(year)[-2:]}{random.randint(10, 12):02d}.{10000 + i}"

        abstract = (
            f"This paper addresses key challenges in {topic_name.lower()}. "
            f"We investigate {base_title.lower()} through rigorous mathematical modeling, "
            f"empirical experimentation, and comprehensive quantitative benchmarking. "
            f"Evaluations on benchmark academic corpora demonstrate substantial improvements "
            f"in throughput, accuracy, and computational efficiency compared to standard baselines. "
            f"The proposed architecture provides a scalable foundation for next-generation systems."
        )

        texts_for_embedding.append(f"{title}. {abstract}")
        paper_records_to_insert.append({
            "title": title,
            "clean_title": clean_title,
            "abstract": abstract,
            "publication_year": year,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "venue": venue,
            "citation_count": citations,
            "primary_topic_id": t_id,
            "topic_name": topic_name,
            "is_duplicate": False
        })

    # 40 Planted Duplicates
    for dup_idx in range(40):
        orig_paper = paper_records_to_insert[dup_idx * 11 % 400]
        dup_type = dup_idx % 4
        if dup_type == 0:
            dup_title = orig_paper["title"].upper()
            dup_doi = None
            dup_arxiv = f"{orig_paper['arxiv_id']}v1" if orig_paper['arxiv_id'] else None
        elif dup_type == 1:
            dup_title = orig_paper["title"].split(" — ")[0] + " (Extended Technical Report)"
            dup_doi = f"{orig_paper['doi']}.ext" if orig_paper['doi'] else None
            dup_arxiv = None
        elif dup_type == 2:
            dup_title = orig_paper["title"].replace("and", "&").replace("for", "in")
            dup_doi = f"{orig_paper['doi']}_v2" if orig_paper['doi'] else None
            dup_arxiv = f"{orig_paper['arxiv_id']}v2" if orig_paper['arxiv_id'] else None
        else:
            dup_title = "A Comprehensive Study on " + orig_paper["title"]
            dup_doi = None
            dup_arxiv = f"{orig_paper['arxiv_id']}.rev" if orig_paper['arxiv_id'] else None

        dup_clean = clean_title_str(dup_title)
        dup_abstract = orig_paper["abstract"]

        texts_for_embedding.append(f"{dup_title}. {dup_abstract}")
        paper_records_to_insert.append({
            "title": dup_title,
            "clean_title": dup_clean,
            "abstract": dup_abstract,
            "publication_year": orig_paper["publication_year"],
            "doi": dup_doi,
            "arxiv_id": dup_arxiv,
            "venue": orig_paper["venue"],
            "citation_count": orig_paper["citation_count"] // 2,
            "primary_topic_id": orig_paper["primary_topic_id"],
            "topic_name": orig_paper["topic_name"],
            "is_duplicate": True,
            "duplicate_of_title": orig_paper["title"]
        })

    print(f"Generating dense semantic embeddings for {len(paper_records_to_insert)} papers...")
    embeddings = generate_embeddings_batch(texts_for_embedding, batch_size=64)

    # Insert papers
    for idx, prec in enumerate(paper_records_to_insert):
        emb_json = json.dumps(embeddings[idx])
        cur.execute(
            """
            INSERT INTO papers (title, clean_title, abstract, publication_year, doi, arxiv_id, venue, citation_count, primary_topic_id, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (prec["title"], prec["clean_title"], prec["abstract"], prec["publication_year"], prec["doi"], prec["arxiv_id"], prec["venue"], prec["citation_count"], prec["primary_topic_id"], emb_json)
        )
        p_id = cur.lastrowid
        prec["id"] = p_id
        papers_inserted.append(prec)

        # Ingest Authors
        selected_authors = random.sample(AUTHOR_POOL, k=random.randint(1, 3))
        for order, (full_author, norm_author, affil) in enumerate(selected_authors, start=1):
            var_name = norm_author if random.random() < 0.35 else full_author
            cur.execute(
                "INSERT INTO paper_authors (paper_id, author_name, normalized_name, affiliation, author_order) VALUES (?, ?, ?, ?, ?)",
                (p_id, var_name, full_author, affil, order)
            )

        # Ingest Paper Sources
        cur.execute(
            "INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url, pdf_url) VALUES (?, ?, ?, ?, ?)",
            (p_id, "OpenAlex", prec["doi"] or f"W_{p_id}", f"https://openalex.org/W{p_id}", f"https://arxiv.org/pdf/{prec['arxiv_id']}.pdf" if prec["arxiv_id"] else "")
        )
        if prec["arxiv_id"]:
            cur.execute(
                "INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url, pdf_url) VALUES (?, ?, ?, ?, ?)",
                (p_id, "arXiv", prec["arxiv_id"], f"https://arxiv.org/abs/{prec['arxiv_id']}", f"https://arxiv.org/pdf/{prec['arxiv_id']}.pdf")
            )

    conn.commit()

    # Ground truth duplicates
    for p in papers_inserted:
        if p.get("is_duplicate"):
            orig = next((x for x in papers_inserted if x["title"] == p["duplicate_of_title"]), None)
            if orig:
                ground_truth_duplicates.append({
                    "original_id": orig["id"],
                    "original_title": orig["title"],
                    "duplicate_id": p["id"],
                    "duplicate_title": p["title"],
                    "relation": "planted_duplicate"
                })

    for full_a, norm_a, affil in AUTHOR_POOL:
        ground_truth_author_resolution.append({
            "canonical_name": full_a,
            "variations": [norm_a, f"{full_a.split()[-1]}, {full_a.split()[0]}", f"{full_a.split()[0][0]}. {full_a.split()[-1]}"],
            "department": affil
        })

    # 5. Follow Relationships (Academic Small-World Network)
    print("Generating Academic Follow Graph Relationships...")
    legit_users = [u for u in users if not u["is_spam"]]
    follow_rows = []

    faculty_researchers = [u for u in legit_users if u["role"] in ("Faculty", "Researcher")]

    for u in legit_users:
        targets = set()
        # Same-department colleagues
        same_dept = [o for o in legit_users if o["dept_id"] == u["dept_id"] and o["id"] != u["id"]]
        # If student, follow 2-4 faculty/researchers in own department
        if u["role"] == "Student":
            dept_advisors = [o for o in same_dept if o["role"] in ("Faculty", "Researcher")]
            if dept_advisors:
                for advisor in random.sample(dept_advisors, k=min(len(dept_advisors), random.randint(2, 4))):
                    targets.add(advisor["id"])

        # Follow peers with shared interests (same & other departments)
        diff_dept = [o for o in legit_users if o["dept_id"] != u["dept_id"] and o["id"] != u["id"]]
        num_follows = random.randint(6, 14)
        k_same = min(len(same_dept), int(num_follows * 0.65))
        k_diff = min(len(diff_dept), num_follows - k_same)

        for t in random.sample(same_dept, k=k_same):
            targets.add(t["id"])
        for t in random.sample(diff_dept, k=k_diff):
            targets.add(t["id"])

        for tid in targets:
            follow_rows.append((u["id"], tid))

    cur.executemany("INSERT OR IGNORE INTO user_followers (follower_id, following_id) VALUES (?, ?)", follow_rows)
    conn.commit()

    # 6. Collections
    print("Seeding Personal Library Collections...")
    coll_rows = []
    for u in legit_users:
        coll_rows.append((u["id"], "Core Readings & Literature", "Foundational papers for ongoing research and course seminars."))
        coll_rows.append((u["id"], "Methodology & Benchmarks", "Key empirical baselines and evaluation frameworks."))
    cur.executemany("INSERT INTO collections (user_id, title, description) VALUES (?, ?, ?)", coll_rows)
    conn.commit()

    cur.execute("SELECT id, user_id FROM collections")
    user_coll_map = {}
    for r in cur.fetchall():
        user_coll_map.setdefault(r[1], []).append(r[0])

    # 7. Time Window Simulation: 6 Months (2026-05-28 to 2026-11-28)
    start_date = datetime(2026, 5, 28, 8, 0, 0)
    end_date = datetime(2026, 11, 28, 20, 0, 0)
    total_days = (end_date - start_date).days  # 184 days (27 weeks)

    qml_topic_id = topic_ids["Quantum Machine Learning"]
    ground_truth_topic_spikes = [{
        "topic_name": "Quantum Machine Learning",
        "topic_id": qml_topic_id,
        "spike_start_day": 155,
        "spike_end_day": 184,
        "spike_multiplier": 5.2,
        "description": "Sudden 5x surge in Quantum ML papers, searches, and library saves following international conference announcements."
    }]

    # Pre-map papers by topic
    papers_by_topic = {}
    for p in papers_inserted:
        papers_by_topic.setdefault(p["primary_topic_id"], []).append(p)

    # Pre-fetch user interest topic IDs
    cur.execute("SELECT user_id, topic_name FROM user_interests")
    user_interest_map = {}
    for r in cur.fetchall():
        uid, tname = r[0], r[1]
        user_interest_map.setdefault(uid, []).append(topic_ids[tname])

    def sample_event_timestamp(is_qml_spike=False):
        """Returns realistic timestamp with diurnal and day-of-week weighting."""
        if is_qml_spike and random.random() < 0.75:
            day_offset = random.randint(155, 184)
        else:
            # Rejection sampling for weekday/weekend weight
            while True:
                day_offset = random.randint(0, total_days)
                d = start_date + timedelta(days=day_offset)
                # Weekdays (Tue-Thu) peak = 1.3, Mon/Fri = 1.0, Sat = 0.6, Sun = 0.45
                w = d.weekday()
                prob = 1.0 if w in (0, 4) else (1.3 if w in (1, 2, 3) else (0.6 if w == 5 else 0.45))
                if random.random() <= prob / 1.3:
                    break

        # Hour distribution: Peak working hours (09:00 - 18:00) vs Evening (19:00 - 23:00)
        r_hour = random.random()
        if r_hour < 0.65:
            hour = random.randint(9, 18)
        elif r_hour < 0.90:
            hour = random.randint(19, 23)
        else:
            hour = random.randint(1, 8)

        dt = start_date + timedelta(days=day_offset, hours=hour, minutes=random.randint(0, 59), seconds=random.randint(0, 59))
        return min(dt, end_date)

    # 8. Library Saves (Target: 10,000+ unique paper-save relationships)
    print("Generating 10,400+ Library Paper Saves (OLTP & Activity Events)...")
    save_rows = []
    activity_save_rows = []

    # 55 legitimate members save on average 190 papers each = ~10,450 saves
    # Ensures no duplicates per (user_id, paper_id)
    total_saved_relationships = 0

    for u in legit_users:
        u_topics = user_interest_map.get(u["id"], [topic_ids["Deep Learning & Neural Architectures"]])
        # Eligible papers: 75% from user's interests, 25% from all papers
        interest_papers = []
        for tid in u_topics:
            interest_papers.extend(papers_by_topic.get(tid, []))

        # Sample ~190 unique papers for this user
        num_saves_for_user = random.randint(188, 196)
        k_interest = min(len(interest_papers), int(num_saves_for_user * 0.75))
        k_other = num_saves_for_user - k_interest

        chosen_paper_objs = list(random.sample(interest_papers, k=k_interest))
        chosen_pids = {p["id"] for p in chosen_paper_objs}
        remaining_pool = [p for p in papers_inserted if p["id"] not in chosen_pids]
        chosen_paper_objs.extend(random.sample(remaining_pool, k=min(k_other, len(remaining_pool))))

        user_coll_id = user_coll_map.get(u["id"], [None])[0]
        for p in chosen_paper_objs:
            is_qml = (p["primary_topic_id"] == qml_topic_id)
            save_dt = sample_event_timestamp(is_qml_spike=is_qml)
            save_time_str = save_dt.strftime("%Y-%m-%d %H:%M:%S")
            rating = random.choice([4, 5, 5, 3, 4])
            notes = random.choice([
                "Key methodology reference for literature review.",
                "Essential baseline for comparative benchmarking.",
                "Relevant theorem on convergence bounds.",
                "Interesting experimental setup; replication candidate.",
                "Recommended reading for semester project."
            ])

            save_rows.append((u["id"], p["id"], user_coll_id, notes, rating, save_time_str))
            activity_save_rows.append((u["id"], "save_paper", "paper", p["id"], json.dumps({"source": "library_explore"}), save_time_str))
            total_saved_relationships += 1

    cur.executemany(
        """
        INSERT OR IGNORE INTO library_saves (user_id, paper_id, collection_id, private_notes, rating, saved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        save_rows
    )
    conn.commit()
    print(f"Inserted {total_saved_relationships} unique library save relationships.")

    # 9. Posts and Comments (Target: 5,000+ Posts and 15,000+ Comments = 20,000+ Combined)
    print("Generating 5,020 Posts & 15,200 Comments (Rich Threaded Academic Conversations)...")
    post_rows = []
    post_tag_rows = []
    activity_post_rows = []
    
    # Generate 4,960 Legitimate Posts + 60 Planted Spam Posts = 5,020 Posts
    post_tracker = []  # will store (post_id, topic_id, created_at_dt)
    
    for post_idx in range(4960):
        poster = random.choice(legit_users)
        poster_topics = user_interest_map.get(poster["id"], [topic_ids["Deep Learning & Neural Architectures"]])
        # 80% from poster's interests, 20% general
        t_id = random.choice(poster_topics) if random.random() < 0.8 else random.choice(list(topic_ids.values()))
        topic_name = next(name for name, tid in topic_ids.items() if tid == t_id)
        
        # Pick discussion template
        title_tmpl, content_tmpl, tags = random.choice(POST_TEMPLATES)
        post_title = title_tmpl.format(topic=topic_name)
        post_content = content_tmpl.format(topic=topic_name)
        
        # 65% of posts attach a real library paper
        attached_paper_id = None
        if random.random() < 0.65 and papers_by_topic.get(t_id):
            attached_paper_id = random.choice(papers_by_topic[t_id])["id"]

        is_qml = (t_id == qml_topic_id)
        post_dt = sample_event_timestamp(is_qml_spike=is_qml)
        post_time_str = post_dt.strftime("%Y-%m-%d %H:%M:%S")
        upvotes = random.randint(2, 35)

        post_rows.append((poster["id"], post_title, post_content, attached_paper_id, t_id, upvotes, 0, post_time_str))

    # 60 Planted Spam Posts from the 5 Spam Accounts (Burst in late October, Days 140-160)
    spam_users = [u for u in users if u["is_spam"]]
    spam_post_titles = [
        "URGENT: Guaranteed Fast Scopus/SCI Paper Acceptance Service $$$",
        "FREE Bitcoin and Crypto Airdrop for Chanakya Students CLICK HERE",
        "Buy Ready-Made Master Thesis and Journal Source Code cheap discount",
        "Guaranteed 500 Citations Boost in 48 Hours contact whatsapp",
        "Fast Degree Certificate & Paper Publishing Clearance Service"
    ]
    for sp_idx in range(60):
        sp_user = random.choice(spam_users)
        sp_title = random.choice(spam_post_titles)
        sp_content = f"Contact fastpublish@boost.net or telegram @cheat_citations for quick degree boost. Free coupons: http://spam.xyz/{sp_idx}"
        day_offset = random.randint(140, 160)
        sp_dt = start_date + timedelta(days=day_offset, hours=random.randint(1, 4), minutes=random.randint(0, 59))
        sp_time_str = sp_dt.strftime("%Y-%m-%d %H:%M:%S")

        post_rows.append((sp_user["id"], sp_title, sp_content, None, None, 0, 0, sp_time_str))

    # Bulk Insert Posts
    cur.executemany(
        """
        INSERT INTO posts (user_id, title, content, attached_paper_id, primary_topic_id, upvote_count, comment_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        post_rows
    )
    conn.commit()

    # Retrieve all post IDs with their metadata
    cur.execute("SELECT id, user_id, primary_topic_id, created_at FROM posts ORDER BY id")
    all_posts = [dict(r) for r in cur.fetchall()]
    print(f"Inserted {len(all_posts)} posts.")

    # Insert Post Tags & Activity Events for Posts
    for p in all_posts:
        pid = p["id"]
        ptime = p["created_at"]
        tid = p["primary_topic_id"]
        p_uid = p["user_id"]

        is_spam_post = (tid is None)
        if not is_spam_post:
            t_name = next((name for name, tid_val in topic_ids.items() if tid_val == tid), "Research")
            clean_tag = t_name.split()[0].replace("&", "")
            post_tag_rows.append((pid, clean_tag))
            post_tag_rows.append((pid, "Research"))
            activity_post_rows.append((p_uid, "post", "post", pid, None, ptime))
        else:
            post_tag_rows.append((pid, "Promo"))
            activity_post_rows.append((p_uid, "post", "post", pid, json.dumps({"flag": "spam_outlier"}), ptime))

    cur.executemany("INSERT INTO post_tags (post_id, tag_name) VALUES (?, ?)", post_tag_rows)
    conn.commit()

    # Generate 15,200 Comments on Posts
    print("Generating 15,200 Threaded Academic Comments...")
    comment_rows = []
    activity_comment_rows = []
    post_comment_counts = {p["id"]: 0 for p in all_posts}
    post_comment_ids = {p["id"]: [] for p in all_posts}

    legit_posts = [p for p in all_posts if p["primary_topic_id"] is not None]

    # Pre-distribute comments: ~3 comments per post on average
    for comm_idx in range(1, 15201):
        target_post = random.choice(legit_posts)
        pid = target_post["id"]
        ptime_dt = datetime.strptime(target_post["created_at"], "%Y-%m-%d %H:%M:%S")
        
        commenter = random.choice(legit_users)
        # Avoid commenting before post creation; comment occurs 1 hour to 14 days after post
        delay_hours = random.randint(1, 336)
        comm_dt = min(ptime_dt + timedelta(hours=delay_hours, minutes=random.randint(0, 59)), end_date)
        comm_time_str = comm_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 35% threaded reply to an existing comment on this post
        parent_id = None
        if post_comment_ids[pid] and random.random() < 0.35:
            parent_id = random.choice(post_comment_ids[pid])
            comment_text = random.choice(THREAD_REPLIES)
        else:
            comment_text = random.choice(COMMENT_TEMPLATES)

        comment_rows.append((comm_idx, pid, commenter["id"], parent_id, comment_text, comm_time_str))
        activity_comment_rows.append((commenter["id"], "comment", "post", pid, None, comm_time_str))
        post_comment_ids[pid].append(comm_idx)
        post_comment_counts[pid] += 1

    cur.executemany(
        """
        INSERT INTO post_comments (id, post_id, user_id, parent_comment_id, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        comment_rows
    )
    conn.commit()

    # Update comment_count on posts in batch
    count_update_rows = [(count, pid) for pid, count in post_comment_counts.items() if count > 0]
    cur.executemany("UPDATE posts SET comment_count = ? WHERE id = ?", count_update_rows)
    conn.commit()
    print("Comments and comment counts updated successfully.")

    # 10. Views and Searches (Target: 20,000+ Views, 10,000+ Searches)
    print("Generating 20,500+ Paper Views and 10,200+ Searches...")
    view_rows = []
    search_history_rows = []
    activity_search_rows = []
    upvote_rows = []
    activity_upvote_rows = []

    # A. 20,500 Paper Views
    for _ in range(20500):
        u = random.choice(legit_users)
        u_topics = user_interest_map.get(u["id"], [topic_ids["Deep Learning & Neural Architectures"]])
        # 70% from user's interests, 30% random
        if random.random() < 0.7:
            tid = random.choice(u_topics)
            cand_papers = papers_by_topic.get(tid, papers_inserted)
        else:
            cand_papers = papers_inserted

        p = random.choice(cand_papers)
        is_qml = (p["primary_topic_id"] == qml_topic_id)
        v_dt = sample_event_timestamp(is_qml_spike=is_qml)
        v_time_str = v_dt.strftime("%Y-%m-%d %H:%M:%S")

        view_rows.append((u["id"], "view_paper", "paper", p["id"], None, v_time_str))

    # B. 10,200 Search Queries
    for _ in range(10200):
        u = random.choice(legit_users)
        u_topics = user_interest_map.get(u["id"], [topic_ids["Deep Learning & Neural Architectures"]])
        # Query matching user's domain
        tid = random.choice(u_topics)
        topic_name = next(name for name, tid_val in topic_ids.items() if tid_val == tid)
        queries_pool = SEARCH_QUERIES_BY_TOPIC.get(topic_name, ["deep learning transformers", "data mining fp growth"])
        q_text = random.choice(queries_pool)

        is_qml = (tid == qml_topic_id)
        s_dt = sample_event_timestamp(is_qml_spike=is_qml)
        s_time_str = s_dt.strftime("%Y-%m-%d %H:%M:%S")
        res_count = random.randint(8, 48)

        search_history_rows.append((u["id"], q_text, res_count, s_time_str))
        activity_search_rows.append((u["id"], "search", "query", None, json.dumps({"query": q_text}), s_time_str))

    # C. 5,500 Upvotes on Posts
    for _ in range(5500):
        u = random.choice(legit_users)
        cand_post = random.choice(legit_posts)
        u_dt = sample_event_timestamp(is_qml_spike=False)
        u_time_str = u_dt.strftime("%Y-%m-%d %H:%M:%S")

        upvote_rows.append((cand_post["id"], u["id"], 1, u_time_str))
        activity_upvote_rows.append((u["id"], "upvote", "post", cand_post["id"], None, u_time_str))

    # Insert Views, Searches, Upvotes
    cur.executemany("INSERT INTO search_history (user_id, query_text, result_count, created_at) VALUES (?, ?, ?, ?)", search_history_rows)
    cur.executemany("INSERT OR IGNORE INTO post_votes (post_id, user_id, vote_value, created_at) VALUES (?, ?, ?, ?)", upvote_rows)
    conn.commit()

    # Bulk Insert all Activity Events (Saves, Posts, Comments, Views, Searches, Upvotes)
    print("Consolidating all activity events into activity_events table...")
    all_activity_events = (
        activity_save_rows +
        activity_post_rows +
        activity_comment_rows +
        view_rows +
        activity_search_rows +
        activity_upvote_rows
    )
    print(f"Bulk inserting {len(all_activity_events)} total events into activity_events...")
    cur.executemany(
        """
        INSERT INTO activity_events (user_id, event_type, target_type, target_id, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        all_activity_events
    )
    conn.commit()

    # 11. Save Ground Truth Benchmark Files
    print("Saving ground truth benchmark files to data/synthetic/...")
    with open(SYNTHETIC_DIR / "ground_truth_duplicates.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth_duplicates, f, indent=2)
    with open(SYNTHETIC_DIR / "ground_truth_author_resolution.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth_author_resolution, f, indent=2)
    with open(SYNTHETIC_DIR / "ground_truth_spam_users.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth_spam_users, f, indent=2)
    with open(SYNTHETIC_DIR / "ground_truth_topic_spikes.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth_topic_spikes, f, indent=2)

    # Standard search benchmark queries
    search_benchmarks = [
        {"query": "deep learning vision transformer attention", "relevant_topic": "Deep Learning & Neural Architectures"},
        {"query": "retrieval augmented generation llm hallucination", "relevant_topic": "Natural Language Processing & LLMs"},
        {"query": "frequent itemset mining fp growth algorithm", "relevant_topic": "Data Mining & Knowledge Discovery"},
        {"query": "distributed consensus raft paxos cloud", "relevant_topic": "Distributed Cloud Systems"},
        {"query": "zero shot object detection visual question answering", "relevant_topic": "Computer Vision & Visual Computing"},
        {"query": "edge computing lorawan iot energy harvesting", "relevant_topic": "Wireless IoT & Edge Computing"},
        {"query": "vlsi compute in memory resistive ram neuromorphic", "relevant_topic": "VLSI Design & Neuromorphic Hardware"},
        {"query": "genomic structural variant calling pangenome alignment", "relevant_topic": "Bioinformatics & Genomic Analytics"},
        {"query": "supply chain inventory stochastic demand optimization", "relevant_topic": "Decision Science & Operations Analytics"},
        {"query": "variational quantum classifiers barren plateaus", "relevant_topic": "Quantum Machine Learning"},
        {"query": "graph neural networks node classification academic", "relevant_topic": "Data Mining & Knowledge Discovery"},
        {"query": "adversarial robustness neural networks certified bounds", "relevant_topic": "Deep Learning & Neural Architectures"},
        {"query": "serverless workflow cold start latency microservices", "relevant_topic": "Distributed Cloud Systems"},
        {"query": "single cell transcriptomics clustering trajectory", "relevant_topic": "Bioinformatics & Genomic Analytics"},
        {"query": "spiking neural network processors event camera", "relevant_topic": "VLSI Design & Neuromorphic Hardware"},
        {"query": "quantum error mitigation noisy intermediate scale", "relevant_topic": "Quantum Machine Learning"},
        {"query": "privacy preserving federated association rules", "relevant_topic": "Data Mining & Knowledge Discovery"},
        {"query": "multi objective portfolio genetic algorithm", "relevant_topic": "Decision Science & Operations Analytics"},
        {"query": "6g sub thz beamforming channel estimation", "relevant_topic": "Wireless IoT & Edge Computing"},
        {"query": "monocular depth estimation transformer backbones", "relevant_topic": "Computer Vision & Visual Computing"}
    ]
    with open(SYNTHETIC_DIR / "ground_truth_search_queries.json", "w", encoding="utf-8") as f:
        json.dump(search_benchmarks, f, indent=2)

    # Standard RAG benchmark queries
    rag_benchmarks = [
        {
            "question": "How do attention mechanisms enhance vision transformers?",
            "topic": "Deep Learning & Neural Architectures",
            "expected_keywords": ["attention", "transformer", "representation", "patch"]
        },
        {
            "question": "What methods mitigate hallucinations in large language models?",
            "topic": "Natural Language Processing & LLMs",
            "expected_keywords": ["retrieval", "verification", "grounding", "citations"]
        },
        {
            "question": "How does the FP-Growth algorithm optimize frequent itemset discovery?",
            "topic": "Data Mining & Knowledge Discovery",
            "expected_keywords": ["fp-growth", "frequent", "tree", "mining"]
        },
        {
            "question": "What are the advantages of compute-in-memory architectures in VLSI?",
            "topic": "VLSI Design & Neuromorphic Hardware",
            "expected_keywords": ["memory", "resistive", "energy", "analog"]
        },
        {
            "question": "What is the role of pangenome graphs in genomic variant calling?",
            "topic": "Bioinformatics & Genomic Analytics",
            "expected_keywords": ["pangenome", "variant", "alignment", "graph"]
        }
    ]
    with open(SYNTHETIC_DIR / "ground_truth_rag_benchmarks.json", "w", encoding="utf-8") as f:
        json.dump(rag_benchmarks, f, indent=2)

    conn.close()
    print("=" * 70)
    print("SYNTHETIC DATASET GENERATION COMPLETED SUCCESSFULLY")
    print("Run `python scripts/verify_dataset.py` to calculate exact database counts and run automated assertions.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Academic Dataset Generator")
    parser.add_argument("--reset", action="store_true", help="Clear existing dynamic records before generation")
    args = parser.parse_args()
    generate_dataset(reset=args.reset)

#!/usr/bin/env python3
"""
Incremental Non-Destructive Dataset Augmentation Script for Chanakya Research Commons.

Checks current counts in the active database (data/chanakya_commons.db) and generates
ONLY the missing records needed to satisfy all project scale targets while preserving
all existing and user-created data.

Targets verified/augmented:
  - Departments: >= 8
  - Research topics: >= 100
  - Members (users): >= 1,000
  - Research papers: >= 2,000 (with synthetic authors, sources, and 384-d embeddings)
  - Collections: >= 1,000
  - Follow relationships: >= 3,000
  - Existing $dummy$ password hashes upgraded to real pbkdf2:sha256 hashes.

Note: Does not fabricate real DOI identifiers, real author attributions, paper URLs,
or external citations. Uses fixed random seed (42) for reproducibility.
"""

import json
import random
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mining.embeddings import generate_embeddings_batch

SEED = 42
DB_PATH = PROJECT_ROOT / "data" / "chanakya_commons.db"

TARGETS = {
    "departments": 9,       # target >= 8
    "topics": 105,          # target >= 100
    "users": 1020,          # target >= 1,000
    "papers": 2050,         # target >= 2,000
    "collections": 1050,    # target >= 1,000
    "user_followers": 3200  # target >= 3,000
}

EXTRA_DEPARTMENTS = [
    ("CYBR", "Department of Cybersecurity & Network Systems", "Information security, cryptography, network defense, and privacy engineering."),
    ("ROBO", "Department of Robotics & Autonomous Systems", "Autonomous navigation, control theory, embedded perception, and human-robot interaction."),
    ("PHYS", "Department of Applied Physics & Quantum Computing", "Quantum information, photonics, condensed matter simulation, and computational physics."),
]

TOPIC_DOMAINS = [
    ("Artificial Intelligence", [
        "Explainable AI & Interpretability", "Federated & Privacy-Preserving ML", "Graph Representation Learning",
        "Reinforcement Learning & Control", "Multimodal Foundation Models", "Continual & Lifelong Learning",
        "Meta-Learning & Few-Shot Adaptation", "Causal Inference in Machine Learning", "Neuro-Symbolic Reasoning",
        "Self-Supervised Audio & Speech", "Generative Diffusion Models", "TinyML & Model Compression",
        "Adversarial Machine Learning", "Neural Radiance Fields & 3D Vision", "Automated Machine Learning (AutoML)",
        "Time-Series Foundation Models"
    ]),
    ("Computer Science", [
        "Stream & Complex Event Processing", "Graph Database Query Optimization", "Distributed Consensus Protocols",
        "Serverless & FaaS Runtime Systems", "Compiler Optimization & Static Analysis", "Formal Verification & Model Checking",
        "High-Performance Parallel Computing", "Approximate Query Processing", "Temporal & Spatial Data Mining",
        "Anomaly Detection in Telemetry", "Knowledge Graph Construction", "Columnar Storage & Vectorized Execution",
        "Differential Privacy Systems", "Software Engineering Analytics", "Program Synthesis & Code Generation"
    ]),
    ("Cybersecurity", [
        "Post-Quantum Cryptography", "Zero-Trust Network Architecture", "Intrusion Detection & Threat Hunting",
        "Hardware Security & Side-Channel Defense", "Blockchain Consensus Security", "Cloud-Native Workload Isolation",
        "Malware Analysis via Graph Embeddings", "Privacy-Preserving Federated Analytics", "Secure Multi-Party Computation",
        "IoT Firmware Vulnerability Analysis"
    ]),
    ("Robotics", [
        "SLAM & Visual-Inertial Odometry", "Motion Planning in Dynamic Environments", "Swarm Robotics & Coordination",
        "Dexterous Manipulation & Grasping", "Sim-to-Real Transfer Learning", "Legged Locomotion & Whole-Body Control",
        "Autonomous Aerial Vehicle Navigation", "Tactile Sensing & Soft Robotics", "Human-Robot Collaborative Assembly"
    ]),
    ("Information Technology", [
        "6G & Terahertz Wireless Networks", "Software-Defined Networking (SDN)", "Mobile Edge Caching & Offloading",
        "Smart Grid Communication Protocols", "Vehicular Ad-Hoc Networks (VANETs)", "Optical & Satellite Networking",
        "Low-Power Wide-Area Networks (LPWAN)", "Digital Twin Infrastructure", "Green & Energy-Aware Cloud Computing"
    ]),
    ("Electronics", [
        "RISC-V Custom Accelerator Design", "Photonic Integrated Circuits", "MEMS Sensors & Actuators",
        "Analog & Mixed-Signal IC Design", "FPGA-Based Deep Learning Inference", "Cryogenic CMOS for Quantum Control",
        "Hardware-Software Co-Design", "Low-Power Wearables & Bio-Sensors", "NoC Architectures for Many-Core SoCs"
    ]),
    ("Biotechnology", [
        "Single-Cell Multi-Omics Integration", "Protein Structure & Ligand Docking", "Metagenomic Microbiome Profiling",
        "Clinical NLP & EHR Phenotyping", "Spatial Transcriptomics Analysis", "Synthetic Biology Circuit Design",
        "Computational Epigenetics", "Biomedical Signal Processing", "Pharmacogenomics & Precision Medicine"
    ]),
    ("Management", [
        "Supply Chain Network Resilience", "Algorithmic Pricing & Revenue Management", "Stochastic Inventory Optimization",
        "Sustainable Operations & ESG Analytics", "Behavioral Decision Modeling", "Financial Risk & Fraud Analytics",
        "Healthcare Operations Scheduling", "Multi-Agent Market Simulation", "Urban Mobility & Transit Optimization"
    ]),
    ("Quantum & Physics", [
        "Quantum Error Correction Codes", "Variational Quantum Eigensolvers", "Quantum Key Distribution",
        "Topological Quantum Computation", "Tensor Network Simulations", "Quantum Sensing & Metrology",
        "Photonic Quantum Computing", "Hybrid Quantum-Classical Optimization"
    ]),
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Akhil", "Akshara", "Amrita", "Ananya", "Anirudh", "Anjali", "Arjun", "Aryan",
    "Bhavya", "Chetan", "Chinmay", "Darshan", "Deepika", "Dev", "Divya", "Esha", "Gaurav", "Harish",
    "Ishaan", "Jhanvi", "Karthik", "Kavya", "Keerthi", "Kiran", "Lakshmi", "Madhav", "Meera", "Nikhil",
    "Nisha", "Pranav", "Priya", "Rahul", "Rajesh", "Rhea", "Rohan", "Sahana", "Sanjay", "Shreya",
    "Siddharth", "Sneha", "Suhas", "Tanvi", "Varun", "Vidya", "Vikram", "Yash", "Zoya", "Nandini"
]

LAST_NAMES = [
    "Deshpande", "Joshi", "Nair", "Rao", "Shetty", "Upadhyay", "Banerjee", "Bhat", "Kulkarni", "Sharma",
    "Patil", "Hegde", "Menon", "Iyer", "Reddy", "Verma", "Gupta", "Mehta", "Kapoor", "Chatterjee",
    "Subramanian", "Krishnamurthy", "Kamath", "Pai", "Murthy", "Agarwal", "Malhotra", "Srinivasan", "Das", "Bose"
]

VENUES = [
    "Chanakya Journal of Computing", "Proceedings of Academic Data Systems", "Symposium on Applied Intelligence",
    "Workshop on Scholarly Information Retrieval", "Annual Conference on Computational Engineering",
    "Transactions on Scientific Analytics", "International Forum on Emerging Architectures"
]

TITLE_PREFIXES = [
    "Scalable", "Adaptive", "Robust", "Efficient", "Hierarchical", "Unified", "Distributed",
    "Interpretable", "Lightweight", "Dynamic", "Self-Supervised", "Privacy-Preserving", "Hybrid",
    "Context-Aware", "Cross-Domain", "Low-Latency", "Automated", "Graph-Based", "Probabilistic", "Incremental"
]

TITLE_METHODS = [
    "Framework", "Architecture", "Optimization", "Pipeline", "Benchmarking", "Analysis",
    "Representation", "Algorithm", "Methodology", "Model", "Protocol", "Evaluation"
]

TITLE_CONTEXTS = [
    "for Large-Scale Academic Repositories", "in Resource-Constrained Environments",
    "under Non-Stationary Workloads", "for Multi-Departmental Collaboration",
    "with Structured Domain Constraints", "for High-Throughput Analytical Streams",
    "using Sparse Matrix Factorizations", "in Heterogeneous Computing Clusters",
    "with Empirical Validation", "for Real-Time Decision Support"
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    random.seed(SEED)
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH), timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    print("=== Incremental Dataset Augmentation ===")

    # 0. Upgrade any $dummy$ password hashes to a real werkzeug password hash
    dummy_count = conn.execute("SELECT COUNT(*) FROM users WHERE password_hash LIKE '%$dummy$%'").fetchone()[0]
    if dummy_count > 0:
        real_hash = generate_password_hash("Chanakya@2026")
        conn.execute("UPDATE users SET password_hash = ? WHERE password_hash LIKE '%$dummy$%'", (real_hash,))
        conn.commit()
        print(f"Upgraded {dummy_count} dummy password hashes to real PBKDF2/scrypt hashes.")

    # 1. Departments (>= 8)
    existing_depts = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM departments").fetchall()}
    added_depts = 0
    for code, name, desc in EXTRA_DEPARTMENTS:
        if len(existing_depts) >= TARGETS["departments"]:
            break
        if code not in existing_depts:
            cur = conn.execute(
                "INSERT INTO departments (code, name, description, faculty_count) VALUES (?, ?, ?, ?)",
                (code, name, desc, random.randint(12, 24))
            )
            existing_depts[code] = cur.lastrowid
            added_depts += 1
    conn.commit()
    dept_ids = list(existing_depts.values())
    print(f"Departments: {len(dept_ids)} (added {added_depts})")

    # 2. Topics (>= 100)
    existing_topics = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM topics").fetchall()}
    existing_slugs = {r["slug"] for r in conn.execute("SELECT slug FROM topics").fetchall()}
    added_topics = 0
    for domain, names in TOPIC_DOMAINS:
        for tname in names:
            if len(existing_topics) >= TARGETS["topics"]:
                break
            if tname not in existing_topics:
                slug = slugify(tname)
                if slug in existing_slugs:
                    slug = f"{slug}-{len(existing_topics)+1}"
                cur = conn.execute(
                    "INSERT INTO topics (name, slug, domain, description) VALUES (?, ?, ?, ?)",
                    (tname, slug, domain, f"Academic research and scholarly inquiry in {tname}.")
                )
                existing_topics[tname] = cur.lastrowid
                existing_slugs.add(slug)
                added_topics += 1
        if len(existing_topics) >= TARGETS["topics"]:
            break
    conn.commit()
    topic_rows = conn.execute("SELECT id, name, domain FROM topics").fetchall()
    topic_ids = [r["id"] for r in topic_rows]
    topic_names = [r["name"] for r in topic_rows]
    print(f"Topics: {len(topic_ids)} (added {added_topics})")

    # 3. Users / Members (>= 1,000)
    existing_usernames = {r["username"].lower() for r in conn.execute("SELECT username FROM users").fetchall()}
    existing_emails = {r["email"].lower() for r in conn.execute("SELECT email FROM users").fetchall()}
    current_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    needed_users = max(0, TARGETS["users"] - current_users)

    shared_pwd_hash = generate_password_hash("Chanakya@2026")
    roles_pool = ["Student"] * 60 + ["Researcher"] * 22 + ["Faculty"] * 18
    base_time = datetime(2026, 5, 25, 9, 0, 0)

    added_users = 0
    new_user_ids = []
    idx = current_users + 1
    while added_users < needed_users:
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        uname = f"{fn.lower()}.{ln.lower()}{idx}"
        email = f"{uname}@chanakya.ac.in"
        idx += 1
        if uname in existing_usernames or email in existing_emails:
            continue
        existing_usernames.add(uname)
        existing_emails.add(email)

        role = random.choice(roles_pool)
        dept_id = dept_ids[added_users % len(dept_ids)]
        prefix = "Prof. " if role == "Faculty" else ("Dr. " if role == "Researcher" and random.random() < 0.35 else "")
        full_name = f"{prefix}{fn} {ln}"
        bio = f"{role} in Chanakya University researching applied computational methods and scholarly data analysis."
        created_at = (base_time + timedelta(days=random.randint(0, 150), hours=random.randint(8, 19))).strftime("%Y-%m-%d %H:%M:%S")

        cur = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, role, department_id, bio, is_spam_flagged, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (uname, email, shared_pwd_hash, full_name, role, dept_id, bio, created_at)
        )
        uid = cur.lastrowid
        new_user_ids.append(uid)

        # Assign 2-4 research interests
        chosen_topics = random.sample(topic_names, k=random.randint(2, 4))
        for tname in chosen_topics:
            conn.execute(
                "INSERT OR IGNORE INTO user_interests (user_id, topic_name, weight) VALUES (?, ?, ?)",
                (uid, tname, round(random.uniform(0.7, 1.0), 2))
            )
        added_users += 1

    conn.commit()
    all_user_rows = conn.execute("SELECT id, department_id, role FROM users WHERE is_spam_flagged = 0").fetchall()
    all_user_ids = [r["id"] for r in all_user_rows]
    print(f"Users: {conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]} (added {added_users})")

    # 4. Papers (>= 2,000) without fabricating DOIs, URLs, or citations
    existing_clean_titles = {r["clean_title"] for r in conn.execute("SELECT clean_title FROM papers").fetchall()}
    current_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    needed_papers = max(0, TARGETS["papers"] - current_papers)

    papers_to_insert = []
    texts_to_embed = []
    attempt = 0
    while len(papers_to_insert) < needed_papers:
        attempt += 1
        t_row = topic_rows[(current_papers + len(papers_to_insert)) % len(topic_rows)]
        topic_id = t_row["id"]
        topic_name = t_row["name"]
        short_topic = topic_name.split("&")[0].strip()

        prefix = random.choice(TITLE_PREFIXES)
        method = random.choice(TITLE_METHODS)
        context = random.choice(TITLE_CONTEXTS)
        variant_tag = f"Study {current_papers + len(papers_to_insert) + 1}" if attempt % 3 == 0 else random.choice([
            "Empirical", "Analytical", "Comparative", "Modular", "Parameterized", "Multi-Stage", "Generalized"
        ])
        title = f"{prefix} {variant_tag} {short_topic} {method} {context}"
        clean_title = re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()
        if clean_title in existing_clean_titles:
            title = f"{title} ({attempt})"
            clean_title = re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()
        existing_clean_titles.add(clean_title)

        abstract = (
            f"This synthetic technical manuscript investigates {topic_name.lower()} through a {prefix.lower()} "
            f"{method.lower()} designed {context.lower()}. Experimental evaluation on synthetic academic benchmarks "
            f"demonstrates consistent improvements in retrieval precision, stability, and computational efficiency."
        )
        pub_year = random.randint(2019, 2026)
        venue = random.choice(VENUES)
        created_at = (base_time + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d %H:%M:%S")
        papers_to_insert.append((title, clean_title, abstract, pub_year, venue, topic_id, created_at))
        texts_to_embed.append(f"{title}. {abstract}")

    if papers_to_insert:
        print(f"Generating 384-d embeddings for {len(texts_to_embed)} new papers...")
        embeddings = generate_embeddings_batch(texts_to_embed)

        for idx_p, (title, clean_title, abstract, pub_year, venue, topic_id, created_at) in enumerate(papers_to_insert):
            emb_json = json.dumps([round(float(x), 5) for x in embeddings[idx_p]])
            cur = conn.execute(
                """
                INSERT INTO papers (title, clean_title, abstract, publication_year, doi, arxiv_id, venue, citation_count, primary_topic_id, embedding_json, created_at)
                VALUES (?, ?, ?, ?, NULL, NULL, ?, 0, ?, ?, ?)
                """,
                (title, clean_title, abstract, pub_year, venue, topic_id, emb_json, created_at)
            )
            pid = cur.lastrowid

            # Synthetic internal authors
            num_authors = random.randint(2, 3)
            for a_ord in range(1, num_authors + 1):
                afn = random.choice(FIRST_NAMES)
                aln = random.choice(LAST_NAMES)
                aname = f"{afn} {aln}"
                conn.execute(
                    """
                    INSERT INTO paper_authors (paper_id, author_name, normalized_name, affiliation, author_order)
                    VALUES (?, ?, ?, 'Chanakya University', ?)
                    """,
                    (pid, aname, aname.lower(), a_ord)
                )

            # Synthetic internal source marker (no fabricated external URLs)
            conn.execute(
                """
                INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url, pdf_url)
                VALUES (?, 'SyntheticCorpus', ?, NULL, NULL)
                """,
                (pid, f"CRC-SYN-{pid}")
            )
        conn.commit()
    print(f"Papers: {conn.execute('SELECT COUNT(*) FROM papers').fetchone()[0]} (added {len(papers_to_insert)})")

    # 5. Collections (>= 1,000)
    current_collections = conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
    needed_collections = max(0, TARGETS["collections"] - current_collections)
    collection_titles = [
        "Core Reading List", "Literature Survey", "Thesis References", "Methodological Notes",
        "Seminar Papers", "Benchmark Studies", "Foundational Works", "Lab Reading Group"
    ]
    added_collections = 0
    for i in range(needed_collections):
        uid = new_user_ids[i % len(new_user_ids)] if new_user_ids else all_user_ids[i % len(all_user_ids)]
        ctitle = f"{random.choice(collection_titles)} #{(i // len(all_user_ids)) + 1}"
        conn.execute(
            "INSERT INTO collections (user_id, title, description, is_public) VALUES (?, ?, ?, 1)",
            (uid, ctitle, "Curated academic reading collection.")
        )
        added_collections += 1
    conn.commit()
    print(f"Collections: {conn.execute('SELECT COUNT(*) FROM collections').fetchone()[0]} (added {added_collections})")

    # 6. Follow relationships (>= 3,000)
    existing_follows = {
        (r["follower_id"], r["following_id"])
        for r in conn.execute("SELECT follower_id, following_id FROM user_followers").fetchall()
    }
    current_follows = len(existing_follows)
    needed_follows = max(0, TARGETS["user_followers"] - current_follows)

    users_by_dept = {}
    for r in all_user_rows:
        users_by_dept.setdefault(r["department_id"], []).append(r["id"])

    added_follows = 0
    attempts = 0
    while added_follows < needed_follows and attempts < needed_follows * 10:
        attempts += 1
        follower = random.choice(all_user_rows)
        fid = follower["id"]
        # 65% same-department follow, 35% cross-department
        if random.random() < 0.65 and len(users_by_dept.get(follower["department_id"], [])) > 1:
            tid = random.choice(users_by_dept[follower["department_id"]])
        else:
            tid = random.choice(all_user_ids)
        if fid == tid or (fid, tid) in existing_follows:
            continue
        existing_follows.add((fid, tid))
        created_at = (base_time + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO user_followers (follower_id, following_id, created_at) VALUES (?, ?, ?)",
            (fid, tid, created_at)
        )
        added_follows += 1
    conn.commit()
    print(f"Follow relationships: {conn.execute('SELECT COUNT(*) FROM user_followers').fetchone()[0]} (added {added_follows})")

    conn.close()
    print("=== Augmentation complete ===")


if __name__ == "__main__":
    main()

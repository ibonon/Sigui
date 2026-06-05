"""
Sigui v4.0 — Marketplace Database Module
Gestion des skills et transactions du marketplace
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import hashlib

class SkillRepository:
    """Repository pour la gestion des skills"""
    
    def __init__(self, db_path: str = "data/sigui_marketplace.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des skills
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                author TEXT NOT NULL,
                price_usdc REAL NOT NULL,
                version TEXT NOT NULL,
                category TEXT NOT NULL,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                sales_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                metadata TEXT NOT NULL
            )
        ''')
        
        # Table des reviews
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_reviews (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills (id)
            )
        ''')
        
        # Table des purchases
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_purchases (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                buyer TEXT NOT NULL,
                amount_usdc REAL NOT NULL,
                transaction_hash TEXT,
                purchased_at TIMESTAMP NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create(self, skill_data: Dict[str, Any]) -> bool:
        """Crée un nouveau skill"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO skills (
                    id, name, description, author, price_usdc, version,
                    category, rating, review_count, sales_count,
                    created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                skill_data['id'],
                skill_data['name'],
                skill_data['description'],
                skill_data['author'],
                skill_data['price_usdc'],
                skill_data['version'],
                skill_data['category'],
                skill_data.get('rating', 0.0),
                skill_data.get('review_count', 0),
                skill_data.get('sales_count', 0),
                skill_data['created_at'].isoformat(),
                skill_data['updated_at'].isoformat(),
                json.dumps(skill_data['metadata'])
            ))
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un skill par son ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM skills WHERE id = ?', (skill_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'author': row[3],
                    'price_usdc': row[4],
                    'version': row[5],
                    'category': row[6],
                    'rating': row[7],
                    'review_count': row[8],
                    'sales_count': row[9],
                    'created_at': datetime.fromisoformat(row[10]),
                    'updated_at': datetime.fromisoformat(row[11]),
                    'metadata': json.loads(row[12])
                }
        except:
            pass
        
        return None
    
    def list(self, 
            category: Optional[str] = None,
            author: Optional[str] = None,
            limit: int = 100,
            offset: int = 0) -> List[Dict[str, Any]]:
        """Liste les skills avec filtres"""
        skills = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM skills WHERE 1=1'
            params = []
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            if author:
                query += ' AND author = ?'
                params.append(author)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            for row in rows:
                skills.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'author': row[3],
                    'price_usdc': row[4],
                    'version': row[5],
                    'category': row[6],
                    'rating': row[7],
                    'review_count': row[8],
                    'sales_count': row[9],
                    'created_at': datetime.fromisoformat(row[10]),
                    'updated_at': datetime.fromisoformat(row[11]),
                    'metadata': json.loads(row[12])
                })
        except:
            pass
        
        return skills
    
    def update(self, skill_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour un skill"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query dynamically
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key == 'metadata':
                    set_clauses.append(f'{key} = ?')
                    params.append(json.dumps(value))
                elif key in ['created_at', 'updated_at']:
                    set_clauses.append(f'{key} = ?')
                    params.append(value.isoformat())
                else:
                    set_clauses.append(f'{key} = ?')
                    params.append(value)
            
            # Always update updated_at
            if 'updated_at' not in updates:
                set_clauses.append('updated_at = ?')
                params.append(datetime.now().isoformat())
            
            params.append(skill_id)
            
            query = f'UPDATE skills SET {", ".join(set_clauses)} WHERE id = ?'
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def delete(self, skill_id: str) -> bool:
        """Supprime un skill"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def increment_sales(self, skill_id: str) -> bool:
        """Incrémente le compteur de ventes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE skills 
                SET sales_count = sales_count + 1,
                    updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), skill_id))
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def add_review(self, 
                  skill_id: str,
                  reviewer: str,
                  rating: int,
                  comment: Optional[str] = None) -> bool:
        """Ajoute une review à un skill"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate review ID
            review_id = hashlib.sha256(
                f"{skill_id}{reviewer}{datetime.now().timestamp()}".encode()
            ).hexdigest()[:32]
            
            # Add review
            cursor.execute('''
                INSERT INTO skill_reviews 
                (id, skill_id, reviewer, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                review_id,
                skill_id,
                reviewer,
                rating,
                comment,
                datetime.now().isoformat()
            ))
            
            # Update skill rating
            cursor.execute('''
                UPDATE skills 
                SET rating = (
                    SELECT AVG(rating) FROM skill_reviews WHERE skill_id = ?
                ),
                review_count = (
                    SELECT COUNT(*) FROM skill_reviews WHERE skill_id = ?
                ),
                updated_at = ?
                WHERE id = ?
            ''', (skill_id, skill_id, datetime.now().isoformat(), skill_id))
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def record_purchase(self,
                       skill_id: str,
                       buyer: str,
                       amount_usdc: float,
                       transaction_hash: Optional[str] = None) -> bool:
        """Enregistre un achat"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate purchase ID
            purchase_id = hashlib.sha256(
                f"{skill_id}{buyer}{datetime.now().timestamp()}".encode()
            ).hexdigest()[:32]
            
            cursor.execute('''
                INSERT INTO skill_purchases 
                (id, skill_id, buyer, amount_usdc, transaction_hash, purchased_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                purchase_id,
                skill_id,
                buyer,
                amount_usdc,
                transaction_hash,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_reviews(self, skill_id: str) -> List[Dict[str, Any]]:
        """Récupère les reviews d'un skill"""
        reviews = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM skill_reviews 
                WHERE skill_id = ? 
                ORDER BY created_at DESC
            ''', (skill_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                reviews.append({
                    'id': row[0],
                    'skill_id': row[1],
                    'reviewer': row[2],
                    'rating': row[3],
                    'comment': row[4],
                    'created_at': datetime.fromisoformat(row[5])
                })
        except:
            pass
        
        return reviews
    
    def get_purchases(self, skill_id: str) -> List[Dict[str, Any]]:
        """Récupère les achats d'un skill"""
        purchases = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM skill_purchases 
                WHERE skill_id = ? 
                ORDER BY purchased_at DESC
            ''', (skill_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                purchases.append({
                    'id': row[0],
                    'skill_id': row[1],
                    'buyer': row[2],
                    'amount_usdc': row[3],
                    'transaction_hash': row[4],
                    'purchased_at': datetime.fromisoformat(row[5])
                })
        except:
            pass
        
        return purchases
    
    def search(self, 
              query: str,
              category: Optional[str] = None,
              min_rating: Optional[float] = None,
              max_price: Optional[float] = None,
              limit: int = 100,
              offset: int = 0) -> List[Dict[str, Any]]:
        """Recherche avancée de skills"""
        skills = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            search_query = '''
                SELECT * FROM skills 
                WHERE (name LIKE ? OR description LIKE ?)
            '''
            params = [f'%{query}%', f'%{query}%']
            
            if category:
                search_query += ' AND category = ?'
                params.append(category)
            
            if min_rating is not None:
                search_query += ' AND rating >= ?'
                params.append(min_rating)
            
            if max_price is not None:
                search_query += ' AND price_usdc <= ?'
                params.append(max_price)
            
            search_query += ' ORDER BY rating DESC, sales_count DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(search_query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            for row in rows:
                skills.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'author': row[3],
                    'price_usdc': row[4],
                    'version': row[5],
                    'category': row[6],
                    'rating': row[7],
                    'review_count': row[8],
                    'sales_count': row[9],
                    'created_at': datetime.fromisoformat(row[10]),
                    'updated_at': datetime.fromisoformat(row[11]),
                    'metadata': json.loads(row[12])
                })
        except:
            pass
        
        return skills
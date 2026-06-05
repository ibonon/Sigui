/**
 * Blockchain Visualizer 3D
 * Composants 3D avancés pour la visualisation des blockchains
 */

class BlockchainVisualizer3D {
    constructor(scene) {
        this.scene = scene;
        this.components = new Map();
        this.animations = new Map();
        
        // Configuration
        this.config = {
            nodeScale: 1.0,
            animationSpeed: 1.0,
            particleDensity: 0.5,
            glowIntensity: 0.3,
        };
        
        // Initialisation
        this.init();
    }
    
    init() {
        // Créer les composants de base
        this.createCoordinateSystem();
        this.createGrid();
        this.createParticleField();
        
        // Démarrer les animations
        this.startAnimations();
    }
    
    createCoordinateSystem() {
        // Axe X (rouge)
        const xAxisGeometry = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-20, 0, 0),
            new THREE.Vector3(20, 0, 0)
        ]);
        const xAxisMaterial = new THREE.LineBasicMaterial({ color: 0xff0000 });
        const xAxis = new THREE.Line(xAxisGeometry, xAxisMaterial);
        this.scene.add(xAxis);
        
        // Axe Y (vert)
        const yAxisGeometry = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, -20, 0),
            new THREE.Vector3(0, 20, 0)
        ]);
        const yAxisMaterial = new THREE.LineBasicMaterial({ color: 0x00ff00 });
        const yAxis = new THREE.Line(yAxisGeometry, yAxisMaterial);
        this.scene.add(yAxis);
        
        // Axe Z (bleu)
        const zAxisGeometry = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, -20),
            new THREE.Vector3(0, 0, 20)
        ]);
        const zAxisMaterial = new THREE.LineBasicMaterial({ color: 0x0000ff });
        const zAxis = new THREE.Line(zAxisGeometry, zAxisMaterial);
        this.scene.add(zAxis);
        
        // Labels
        this.createAxisLabel('X', new THREE.Vector3(21, 0, 0), 0xff0000);
        this.createAxisLabel('Y', new THREE.Vector3(0, 21, 0), 0x00ff00);
        this.createAxisLabel('Z', new THREE.Vector3(0, 0, 21), 0x0000ff);
    }
    
    createAxisLabel(text, position, color) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 64;
        canvas.height = 64;
        
        // Fond transparent
        context.clearRect(0, 0, canvas.width, canvas.height);
        
        // Texte
        context.font = 'bold 48px Arial';
        context.fillStyle = `rgb(${color >> 16}, ${(color >> 8) & 255}, ${color & 255})`;
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(text, canvas.width / 2, canvas.height / 2);
        
        // Texture
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);
        
        sprite.position.copy(position);
        sprite.scale.set(4, 4, 1);
        
        this.scene.add(sprite);
    }
    
    createGrid() {
        // Grille principale
        const gridSize = 40;
        const gridDivisions = 40;
        
        const gridHelper = new THREE.GridHelper(gridSize, gridDivisions, 0x444444, 0x222222);
        gridHelper.position.y = -0.1; // Juste en dessous des autres objets
        this.scene.add(gridHelper);
        
        // Points de repère
        this.createGridMarkers();
    }
    
    createGridMarkers() {
        const markerPositions = [
            { x: -15, z: -15, label: 'Ethereum' },
            { x: 15, z: -15, label: 'Solana' },
            { x: -15, z: 15, label: 'Cosmos' },
            { x: 0, z: -10, label: 'Aave' },
            { x: 10, z: 0, label: 'Compound' },
            { x: -10, z: 0, label: 'MakerDAO' },
            { x: 0, z: 10, label: 'Uniswap' },
        ];
        
        markerPositions.forEach(({ x, z, label }) => {
            // Marqueur
            const markerGeometry = new THREE.CircleGeometry(0.5, 16);
            const markerMaterial = new THREE.MeshBasicMaterial({
                color: 0x00ffff,
                transparent: true,
                opacity: 0.5,
            });
            const marker = new THREE.Mesh(markerGeometry, markerMaterial);
            
            marker.position.set(x, 0.1, z);
            marker.rotation.x = -Math.PI / 2;
            
            this.scene.add(marker);
            
            // Label
            this.createGridLabel(label, new THREE.Vector3(x, 0.2, z));
        });
    }
    
    createGridLabel(text, position) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 128;
        canvas.height = 32;
        
        // Fond
        context.fillStyle = 'rgba(0, 0, 0, 0.7)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Texte
        context.font = 'bold 16px Arial';
        context.fillStyle = '#00ffff';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(text, canvas.width / 2, canvas.height / 2);
        
        // Texture
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);
        
        sprite.position.copy(position);
        sprite.scale.set(6, 1.5, 1);
        
        this.scene.add(sprite);
    }
    
    createParticleField() {
        const particleCount = 500;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        
        for (let i = 0; i < particleCount; i++) {
            // Position aléatoire dans un volume
            const x = (Math.random() - 0.5) * 50;
            const y = (Math.random() - 0.5) * 30;
            const z = (Math.random() - 0.5) * 50;
            
            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;
            
            // Couleur cyan avec variation
            colors[i * 3] = 0;
            colors[i * 3 + 1] = 1;
            colors[i * 3 + 2] = Math.random() * 0.5 + 0.5;
            
            // Taille aléatoire
            sizes[i] = Math.random() * 0.5 + 0.1;
        }
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
        
        const material = new THREE.PointsMaterial({
            size: 0.1,
            vertexColors: true,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending,
        });
        
        const particles = new THREE.Points(geometry, material);
        this.scene.add(particles);
        
        this.components.set('particleField', particles);
    }
    
    startAnimations() {
        // Animation des particules
        const particleField = this.components.get('particleField');
        if (particleField) {
            this.animateParticles(particleField);
        }
        
        // Animation des marqueurs
        // Animation des axes
    }
    
    animateParticles(particles) {
        const positions = particles.geometry.attributes.position.array;
        const originalPositions = positions.slice(); // Copie des positions originales
        
        const animate = () => {
            const time = Date.now() * 0.001 * this.config.animationSpeed;
            
            for (let i = 0; i < positions.length / 3; i++) {
                const idx = i * 3;
                
                // Mouvement sinusoïdal
                const offsetX = Math.sin(time + i * 0.1) * 0.5;
                const offsetY = Math.cos(time * 0.7 + i * 0.05) * 0.3;
                const offsetZ = Math.sin(time * 0.3 + i * 0.02) * 0.4;
                
                positions[idx] = originalPositions[idx] + offsetX;
                positions[idx + 1] = originalPositions[idx + 1] + offsetY;
                positions[idx + 2] = originalPositions[idx + 2] + offsetZ;
            }
            
            particles.geometry.attributes.position.needsUpdate = true;
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    // Méthodes pour créer des composants spécifiques
    createTransactionBeam(from, to, color = 0x00ffff, duration = 2000) {
        const direction = new THREE.Vector3().subVectors(to, from);
        const distance = from.distanceTo(to);
        
        const geometry = new THREE.CylinderGeometry(0.05, 0.05, distance, 8);
        geometry.rotateZ(Math.PI / 2);
        
        const material = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.8,
        });
        
        const beam = new THREE.Mesh(geometry, material);
        
        // Positionner au milieu
        const midPoint = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
        beam.position.copy(midPoint);
        
        // Orienter vers la cible
        beam.lookAt(to);
        
        this.scene.add(beam);
        
        // Animation de disparition
        let opacity = 0.8;
        const fadeOut = () => {
            opacity -= 0.02;
            material.opacity = opacity;
            
            if (opacity > 0) {
                requestAnimationFrame(fadeOut);
            } else {
                this.scene.remove(beam);
            }
        };
        
        setTimeout(fadeOut, duration);
        
        return beam;
    }
    
    createDataStream(from, to, particleCount = 20, color = 0x00ffff) {
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            const t = i / particleCount;
            
            positions[i * 3] = from.x + (to.x - from.x) * t;
            positions[i * 3 + 1] = from.y + (to.y - from.y) * t;
            positions[i * 3 + 2] = from.z + (to.z - from.z) * t;
            
            colors[i * 3] = (color >> 16 & 255) / 255;
            colors[i * 3 + 1] = (color >> 8 & 255) / 255;
            colors[i * 3 + 2] = (color & 255) / 255;
        }
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        
        const material = new THREE.PointsMaterial({
            size: 0.2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
        });
        
        const stream = new THREE.Points(geometry, material);
        
        stream.userData = {
            from: from.clone(),
            to: to.clone(),
            speed: 0.01,
            offset: Math.random() * Math.PI * 2,
        };
        
        this.scene.add(stream);
        
        // Animation
        this.animateDataStream(stream);
        
        return stream;
    }
    
    animateDataStream(stream) {
        const positions = stream.geometry.attributes.position.array;
        const userData = stream.userData;
        
        const animate = () => {
            const time = Date.now() * 0.001;
            
            for (let i = 0; i < positions.length / 3; i++) {
                const t = (i / (positions.length / 3) + time * userData.speed + userData.offset) % 1;
                
                positions[i * 3] = userData.from.x + (userData.to.x - userData.from.x) * t;
                positions[i * 3 + 1] = userData.from.y + (userData.to.y - userData.from.y) * t;
                positions[i * 3 + 2] = userData.from.z + (userData.to.z - userData.from.z) * t;
                
                // Mouvement sinusoïdal
                const wave = Math.sin(t * Math.PI * 2) * 0.5;
                positions[i * 3 + 1] += wave;
            }
            
            stream.geometry.attributes.position.needsUpdate = true;
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    createThreatVisualization(position, severity = 'medium', duration = 5000) {
        let color;
        let size;
        
        switch (severity) {
            case 'low':
                color = 0xffff00;
                size = 2;
                break;
            case 'medium':
                color = 0xff8800;
                size = 3;
                break;
            case 'high':
                color = 0xff0000;
                size = 4;
                break;
            case 'critical':
                color = 0xff00ff;
                size = 5;
                break;
            default:
                color = 0xff8800;
                size = 3;
        }
        
        // Sphère principale
        const sphereGeometry = new THREE.SphereGeometry(size, 32, 32);
        const sphereMaterial = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.7,
            blending: THREE.AdditiveBlending,
        });
        
        const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
        sphere.position.copy(position);
        
        this.scene.add(sphere);
        
        // Halo
        const haloGeometry = new THREE.SphereGeometry(size * 1.5, 32, 32);
        const haloMaterial = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.3,
            side: THREE.BackSide,
        });
        
        const halo = new THREE.Mesh(haloGeometry, haloMaterial);
        halo.position.copy(position);
        
        this.scene.add(halo);
        
        // Particules
        const particleCount = 50;
        const particleGeometry = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);
        const particleColors = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            const radius = Math.random() * size * 2 + size;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;
            
            particlePositions[i * 3] = position.x + radius * Math.sin(phi) * Math.cos(theta);
            particlePositions[i * 3 + 1] = position.y + radius * Math.cos(phi);
            particlePositions[i * 3 + 2] = position.z + radius * Math.sin(phi) * Math.sin(theta);
            
            particleColors[i * 3] = (color >> 16 & 255) / 255;
            particleColors[i * 3 + 1] = (color >> 8 & 255) / 255;
            particleColors[i * 3 + 2] = (color & 255) / 255;
        }
        
        particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        particleGeometry.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));
        
        const particleMaterial = new THREE.PointsMaterial({
            size: 0.2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
        });
        
        const particles = new THREE.Points(particleGeometry, particleMaterial);
        
        this.scene.add(particles);
        
        // Animation
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = elapsed / duration;
            
            if (progress >= 1) {
                this.scene.remove(sphere);
                this.scene.remove(halo);
                this.scene.remove(particles);
                return;
            }
            
            // Animation de pulsation
            const pulse = 1 + Math.sin(elapsed * 0.005) * 0.2;
            sphere.scale.setScalar(pulse);
            halo.scale.setScalar(pulse);
            
            // Animation des particules
            const particlePositions = particles.geometry.attributes.position.array;
            const time = Date.now() * 0.001;
            
            for (let i = 0; i < particlePositions.length / 3; i++) {
                const idx = i * 3;
                const radius = Math.sqrt(
                    Math.pow(particlePositions[idx] - position.x, 2) +
                    Math.pow(particlePositions[idx + 1] - position.y, 2) +
                    Math.pow(particlePositions[idx + 2] - position.z, 2)
                );
                
                const newRadius = radius * (1 + Math.sin(time + i) * 0.1);
                const theta = Math.atan2(
                    particlePositions[idx + 2] - position.z,
                    particlePositions[idx] - position.x
                );
                const phi = Math.acos(
                    (particlePositions[idx + 1] - position.y) / radius
                );
                
                particlePositions[idx] = position.x + newRadius * Math.sin(phi) * Math.cos(theta);
                particlePositions[idx + 1] = position.y + newRadius * Math.cos(phi);
                particlePositions[idx + 2] = position.z + newRadius * Math.sin(phi) * Math.sin(theta);
            }
            
            particles.geometry.attributes.position.needsUpdate = true;
            
            requestAnimationFrame(animate);
        };
        
        animate();
        
        return {
            sphere,
            halo,
            particles,
        };
    }
    
    createAgentAvatar(position, agentId, color = 0x00ff00) {
        // Sphère principale
        const sphereGeometry = new THREE.SphereGeometry(0.5, 16, 16);
        const sphereMaterial = new THREE.MeshPhongMaterial({
            color: color,
            shininess: 30,
            emissive: color,
            emissiveIntensity: 0.3,
        });
        
        const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
        sphere.position.copy(position);
        
        // Halo
        const haloGeometry = new THREE.SphereGeometry(0.7, 32, 32);
        const haloMaterial = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.2,
            side: THREE.BackSide,
        });
        
        const halo = new THREE.Mesh(haloGeometry, haloMaterial);
        halo.position.copy(position);
        
        sphere.add(halo);
        
        // Label
        const label = this.createAgentLabel(agentId);
        label.position.y = 1;
        sphere.add(label);
        
        this.scene.add(sphere);
        
        // Animation
        this.animateAgentAvatar(sphere);
        
        return sphere;
    }
    
    createAgentLabel(agentId) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 128;
        canvas.height = 32;
        
        // Fond
        context.fillStyle = 'rgba(0, 0, 0, 0.7)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Texte
        context.font = 'bold 12px Arial';
        context.fillStyle = '#00ff00';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(`Agent ${agentId.substring(0, 8)}`, canvas.width / 2, canvas.height / 2);
        
        // Texture
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);
        
        sprite.scale.set(4, 1, 1);
        
        return sprite;
    }
    
    animateAgentAvatar(avatar) {
        const startPosition = avatar.position.clone();
        
        const animate = () => {
            const time = Date.now() * 0.001;
            
            // Lévitation
            avatar.position.y = startPosition.y + Math.sin(time) * 0.5;
            
            // Rotation
            avatar.rotation.y += 0.01;
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    createNetworkConnection(from, to, color = 0x00ffff, width = 0.1) {
        const points = [];
        points.push(new THREE.Vector3(from.x, from.y, from.z));
        points.push(new THREE.Vector3(to.x, to.y, to.z));
        
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.3,
            linewidth: width,
        });
        
        const line = new THREE.Line(geometry, material);
        this.scene.add(line);
        
        return line;
    }
    
    createBlockchainNode(position, chain, status = 'healthy') {
        let color;
        
        switch (chain) {
            case 'ethereum':
                color = 0x627eea;
                break;
            case 'solana':
                color = 0x00ffa3;
                break;
            case 'cosmos':
                color = 0x2e3148;
                break;
            case 'aave':
                color = 0xb6509e;
                break;
            case 'compound':
                color = 0x00d395;
                break;
            case 'makerdao':
                color = 0x1aab9b;
                break;
            case 'uniswap':
                color = 0xff007a;
                break;
            default:
                color = 0x888888;
        }
        
        // Ajuster la couleur basée sur le statut
        if (status === 'warning') {
            color = 0xffaa00;
        } else if (status === 'critical') {
            color = 0xff0000;
        }
        
        // Géométrie icosaèdre
        const geometry = new THREE.IcosahedronGeometry(2, 2);
        const material = new THREE.MeshPhongMaterial({
            color: color,
            shininess: 100,
            specular: 0x444444,
            emissive: color,
            emissiveIntensity: 0.2,
            transparent: true,
            opacity: 0.9,
        });
        
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(position);
        mesh.userData = { chain, status, type: 'blockchain_node' };
        
        // Halo
        const haloGeometry = new THREE.SphereGeometry(2.4, 32, 32);
        const haloMaterial = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.1,
            side: THREE.BackSide,
        });
        
        const halo = new THREE.Mesh(haloGeometry, haloMaterial);
        mesh.add(halo);
        
        // Label
        const label = this.createNodeLabel(chain);
        label.position.y = 3;
        mesh.add(label);
        
        this.scene.add(mesh);
        
        return mesh;
    }
    
    createNodeLabel(chain) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 128;
        canvas.height = 32;
        
        // Fond
        context.fillStyle = 'rgba(0, 0, 0, 0.8)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Texte
        context.font = 'bold 14px Arial';
        context.fillStyle = '#ffffff';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(chain.toUpperCase(), canvas.width / 2, canvas.height / 2);
        
        // Texture
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(material);
        
        sprite.scale.set(6, 1.5, 1);
        
        return sprite;
    }
    
    // Méthodes utilitaires
    updateNodeStatus(node, newStatus) {
        if (!node.userData || node.userData.type !== 'blockchain_node') {
            return;
        }
        
        node.userData.status = newStatus;
        
        let color;
        switch (node.userData.chain) {
            case 'ethereum':
                color = 0x627eea;
                break;
            case 'solana':
                color = 0x00ffa3;
                break;
            case 'cosmos':
                color = 0x2e3148;
                break;
            case 'aave':
                color = 0xb6509e;
                break;
            case 'compound':
                color = 0x00d395;
                break;
            case 'makerdao':
                color = 0x1aab9b;
                break;
            case 'uniswap':
                color = 0xff007a;
                break;
            default:
                color = 0x888888;
        }
        
        if (newStatus === 'warning') {
            color = 0xffaa00;
        } else if (newStatus === 'critical') {
            color = 0xff0000;
        }
        
        node.material.color.set(color);
        node.material.emissive.set(color);
        
        // Animer en cas de changement critique
        if (newStatus === 'critical') {
            this.pulseNode(node);
        }
    }
    
    pulseNode(node) {
        const originalScale = node.scale.clone();
        
        const pulse = () => {
            const time = Date.now() * 0.001;
            const scale = 1 + Math.sin(time * 5) * 0.1;
            
            node.scale.copy(originalScale).multiplyScalar(scale);
            
            requestAnimationFrame(pulse);
        };
        
        pulse();
        
        // Arrêter après 5 secondes
        setTimeout(() => {
            node.scale.copy(originalScale);
        }, 5000);
    }
    
    // Méthodes de contrôle
    setAnimationSpeed(speed) {
        this.config.animationSpeed = speed;
    }
    
    setParticleDensity(density) {
        this.config.particleDensity = density;
        
        // Mettre à jour le champ de particules
        const particleField = this.components.get('particleField');
        if (particleField) {
            this.updateParticleField(particleField, density);
        }
    }
    
    updateParticleField(particles, density) {
        // À implémenter: ajuster la densité des particules
    }
    
    clearAll() {
        // Supprimer tous les composants créés
        this.components.forEach((component) => {
            this.scene.remove(component);
        });
        
        this.components.clear();
        this.animations.clear();
    }
    
    // Méthodes de débogage
    logComponents() {
        console.log('Composants 3D:');
        this.components.forEach((component, name) => {
            console.log(`- ${name}:`, component);
        });
    }
    
    getComponentCount() {
        return this.components.size;
    }
}

// Export pour une utilisation globale
if (typeof window !== 'undefined') {
    window.BlockchainVisualizer3D = BlockchainVisualizer3D;
}
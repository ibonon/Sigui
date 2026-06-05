/**
 * War Room 3D Visualization
 * Interface de commandement avancée pour la surveillance cross-chain
 */

class WarRoom3D {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.clock = new THREE.Clock();
        
        // Éléments 3D
        this.blockchainNodes = new Map();
        this.agentAvatars = new Map();
        this.threatVisualizations = new Map();
        this.dataStreams = new Map();
        
        // État du système
        this.systemStatus = {
            ethereum: { status: 'healthy', threats: 0 },
            solana: { status: 'healthy', threats: 0 },
            cosmos: { status: 'healthy', threats: 0 },
            aave: { status: 'healthy', threats: 0 },
            compound: { status: 'healthy', threats: 0 },
            makerdao: { status: 'healthy', threats: 0 },
            uniswap: { status: 'healthy', threats: 0 },
        };
        
        // Configuration
        this.config = {
            nodeRadius: 2,
            connectionWidth: 0.1,
            animationSpeed: 1.0,
            autoRotate: true,
            showLabels: true,
            particleCount: 1000,
        };
        
        // Initialisation
        this.init();
    }
    
    init() {
        // Initialiser Three.js
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a1a);
        
        // Ajouter des étoiles en arrière-plan
        this.addStars();
        
        // Caméra
        this.camera = new THREE.PerspectiveCamera(
            75,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(0, 20, 30);
        
        // Rendu
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        // Contrôles
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.autoRotate = this.config.autoRotate;
        this.controls.autoRotateSpeed = 0.5;
        
        // Lumière
        this.addLights();
        
        // Créer les éléments du système
        this.createBlockchainNodes();
        this.createConnections();
        this.createDataStreams();
        
        // Événements
        window.addEventListener('resize', () => this.onWindowResize());
        
        // Démarrer l'animation
        this.animate();
        
        // Charger les données initiales
        this.loadInitialData();
    }
    
    addStars() {
        const starGeometry = new THREE.BufferGeometry();
        const starCount = 5000;
        const positions = new Float32Array(starCount * 3);
        
        for (let i = 0; i < starCount * 3; i += 3) {
            positions[i] = (Math.random() - 0.5) * 2000;
            positions[i + 1] = (Math.random() - 0.5) * 2000;
            positions[i + 2] = (Math.random() - 0.5) * 2000;
        }
        
        starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        
        const starMaterial = new THREE.PointsMaterial({
            color: 0xffffff,
            size: 0.7,
            transparent: true,
        });
        
        const stars = new THREE.Points(starGeometry, starMaterial);
        this.scene.add(stars);
    }
    
    addLights() {
        // Lumière ambiante
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        
        // Lumière directionnelle principale
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 20, 15);
        this.scene.add(directionalLight);
        
        // Lumières ponctuelles colorées
        const colors = [0xff0000, 0x00ff00, 0x0000ff, 0xffff00, 0xff00ff, 0x00ffff];
        const positions = [
            { x: -15, y: 10, z: -15 },
            { x: 15, y: 10, z: -15 },
            { x: -15, y: 10, z: 15 },
            { x: 15, y: 10, z: 15 },
            { x: 0, y: 20, z: 0 },
            { x: 0, y: -10, z: 0 },
        ];
        
        colors.forEach((color, index) => {
            const pointLight = new THREE.PointLight(color, 0.5, 50);
            pointLight.position.set(positions[index].x, positions[index].y, positions[index].z);
            this.scene.add(pointLight);
        });
    }
    
    createBlockchainNodes() {
        const nodePositions = {
            ethereum: { x: -15, y: 0, z: -15 },
            solana: { x: 15, y: 0, z: -15 },
            cosmos: { x: -15, y: 0, z: 15 },
            aave: { x: 0, y: 8, z: -10 },
            compound: { x: 10, y: 8, z: 0 },
            makerdao: { x: -10, y: 8, z: 0 },
            uniswap: { x: 0, y: 8, z: 10 },
        };
        
        Object.entries(nodePositions).forEach(([chain, position]) => {
            const node = this.createNode(chain, position);
            this.blockchainNodes.set(chain, node);
            this.scene.add(node);
        });
    }
    
    createNode(chain, position) {
        // Géométrie
        const geometry = new THREE.IcosahedronGeometry(this.config.nodeRadius, 2);
        
        // Matériau avec effet de brillance
        const material = new THREE.MeshPhongMaterial({
            color: this.getChainColor(chain),
            shininess: 100,
            specular: 0x444444,
            emissive: this.getChainColor(chain),
            emissiveIntensity: 0.2,
            transparent: true,
            opacity: 0.9,
        });
        
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(position.x, position.y, position.z);
        mesh.userData = { chain, type: 'blockchain_node' };
        
        // Ajouter un halo
        const haloGeometry = new THREE.SphereGeometry(this.config.nodeRadius * 1.2, 32, 32);
        const haloMaterial = new THREE.MeshBasicMaterial({
            color: this.getChainColor(chain),
            transparent: true,
            opacity: 0.1,
            side: THREE.BackSide,
        });
        
        const halo = new THREE.Mesh(haloGeometry, haloMaterial);
        halo.position.set(0, 0, 0);
        mesh.add(halo);
        
        // Ajouter un label
        if (this.config.showLabels) {
            this.addLabel(mesh, chain);
        }
        
        return mesh;
    }
    
    getChainColor(chain) {
        const colors = {
            ethereum: 0x627eea,
            solana: 0x00ffa3,
            cosmos: 0x2e3148,
            aave: 0xb6509e,
            compound: 0x00d395,
            makerdao: 0x1aab9b,
            uniswap: 0xff007a,
        };
        
        return colors[chain] || 0x888888;
    }
    
    addLabel(mesh, text) {
        // Créer un canvas pour le texte
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 128;
        
        // Fond
        context.fillStyle = 'rgba(0, 0, 0, 0.8)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Texte
        context.font = 'bold 24px Arial';
        context.fillStyle = '#ffffff';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(text.toUpperCase(), canvas.width / 2, canvas.height / 2);
        
        // Texture
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        
        // Position au-dessus du nœud
        sprite.position.y = this.config.nodeRadius * 2;
        sprite.scale.set(8, 4, 1);
        
        mesh.add(sprite);
    }
    
    createConnections() {
        const connections = [
            ['ethereum', 'aave'],
            ['ethereum', 'compound'],
            ['ethereum', 'makerdao'],
            ['ethereum', 'uniswap'],
            ['solana', 'aave'],
            ['cosmos', 'aave'],
            ['aave', 'compound'],
            ['compound', 'makerdao'],
            ['makerdao', 'uniswap'],
        ];
        
        connections.forEach(([from, to]) => {
            const fromNode = this.blockchainNodes.get(from);
            const toNode = this.blockchainNodes.get(to);
            
            if (fromNode && toNode) {
                this.createConnectionLine(fromNode.position, toNode.position);
            }
        });
    }
    
    createConnectionLine(fromPos, toPos) {
        const points = [];
        points.push(new THREE.Vector3(fromPos.x, fromPos.y, fromPos.z));
        points.push(new THREE.Vector3(toPos.x, toPos.y, toPos.z));
        
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
            color: 0x00ffff,
            transparent: true,
            opacity: 0.3,
            linewidth: this.config.connectionWidth,
        });
        
        const line = new THREE.Line(geometry, material);
        this.scene.add(line);
        
        // Ajouter des particules qui se déplacent le long de la ligne
        this.addDataParticles(fromPos, toPos);
    }
    
    addDataParticles(fromPos, toPos) {
        const particleCount = 20;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            const t = i / particleCount;
            positions[i * 3] = fromPos.x + (toPos.x - fromPos.x) * t;
            positions[i * 3 + 1] = fromPos.y + (toPos.y - fromPos.y) * t;
            positions[i * 3 + 2] = fromPos.z + (toPos.z - fromPos.z) * t;
            
            // Couleur cyan pour les données
            colors[i * 3] = 0;
            colors[i * 3 + 1] = 1;
            colors[i * 3 + 2] = 1;
        }
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        
        const material = new THREE.PointsMaterial({
            size: 0.3,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
        });
        
        const particles = new THREE.Points(geometry, material);
        particles.userData = {
            fromPos: new THREE.Vector3(fromPos.x, fromPos.y, fromPos.z),
            toPos: new THREE.Vector3(toPos.x, toPos.y, toPos.z),
            speed: 0.01 + Math.random() * 0.02,
            offset: Math.random() * Math.PI * 2,
        };
        
        this.scene.add(particles);
        this.dataStreams.set(particles.uuid, particles);
    }
    
    createDataStreams() {
        // Créer des flux de données animés entre les nœuds
        setInterval(() => {
            this.updateDataStreams();
        }, 100);
    }
    
    updateDataStreams() {
        this.dataStreams.forEach((particles) => {
            const positions = particles.geometry.attributes.position.array;
            const userData = particles.userData;
            
            for (let i = 0; i < positions.length / 3; i++) {
                const t = (i / (positions.length / 3) + Date.now() * userData.speed * 0.001 + userData.offset) % 1;
                
                positions[i * 3] = userData.fromPos.x + (userData.toPos.x - userData.fromPos.x) * t;
                positions[i * 3 + 1] = userData.fromPos.y + (userData.toPos.y - userData.fromPos.y) * t;
                positions[i * 3 + 2] = userData.fromPos.z + (userData.toPos.z - userData.fromPos.z) * t;
                
                // Ajouter un mouvement sinusoïdal pour l'effet
                const wave = Math.sin(t * Math.PI * 2) * 0.5;
                positions[i * 3 + 1] += wave;
            }
            
            particles.geometry.attributes.position.needsUpdate = true;
        });
    }
    
    onWindowResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();
        
        // Animer les nœuds
        this.blockchainNodes.forEach((node) => {
            node.rotation.y += delta * 0.2;
            
            // Effet de pulsation
            const scale = 1 + Math.sin(Date.now() * 0.001) * 0.05;
            node.scale.setScalar(scale);
        });
        
        // Mettre à jour les contrôles
        this.controls.update();
        
        // Rendu
        this.renderer.render(this.scene, this.camera);
    }
    
    loadInitialData() {
        // Charger les données système via WebSocket
        this.connectWebSocket();
        
        // Mettre à jour l'interface
        this.updateDashboard();
    }
    
    connectWebSocket() {
        const ws = new WebSocket('ws://localhost:8000/ws/war-room');
        
        ws.onopen = () => {
            console.log('WebSocket War Room connecté');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        ws.onclose = () => {
            console.log('WebSocket War Room déconnecté, reconnexion...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'system_status':
                this.updateSystemStatus(data.payload);
                break;
                
            case 'threat_detected':
                this.visualizeThreat(data.payload);
                break;
                
            case 'agent_activity':
                this.updateAgentActivity(data.payload);
                break;
                
            case 'transaction_alert':
                this.showTransactionAlert(data.payload);
                break;
        }
    }
    
    updateSystemStatus(status) {
        this.systemStatus = status;
        
        // Mettre à jour les couleurs des nœuds
        Object.entries(status).forEach(([chain, chainStatus]) => {
            const node = this.blockchainNodes.get(chain);
            if (node) {
                const material = node.material;
                
                // Changer la couleur basée sur le statut
                let color;
                switch (chainStatus.status) {
                    case 'healthy':
                        color = this.getChainColor(chain);
                        material.emissiveIntensity = 0.2;
                        break;
                    case 'warning':
                        color = 0xffaa00;
                        material.emissiveIntensity = 0.5;
                        break;
                    case 'critical':
                        color = 0xff0000;
                        material.emissiveIntensity = 0.8;
                        break;
                }
                
                material.color.set(color);
                material.emissive.set(color);
                
                // Animer en cas de menace
                if (chainStatus.threats > 0) {
                    this.pulseNode(node);
                }
            }
        });
        
        // Mettre à jour le dashboard
        this.updateDashboard();
    }
    
    pulseNode(node) {
        // Créer une onde de choc
        const shockwaveGeometry = new THREE.SphereGeometry(0.5, 32, 32);
        const shockwaveMaterial = new THREE.MeshBasicMaterial({
            color: 0xff0000,
            transparent: true,
            opacity: 0.7,
        });
        
        const shockwave = new THREE.Mesh(shockwaveGeometry, shockwaveMaterial);
        shockwave.position.copy(node.position);
        this.scene.add(shockwave);
        
        // Animation de l'onde
        let scale = 1;
        const animate = () => {
            scale += 0.1;
            shockwave.scale.setScalar(scale);
            shockwaveMaterial.opacity -= 0.02;
            
            if (shockwaveMaterial.opacity > 0) {
                requestAnimationFrame(animate);
            } else {
                this.scene.remove(shockwave);
            }
        };
        
        animate();
    }
    
    visualizeThreat(threatData) {
        const { chain, severity, description, transaction_hash } = threatData;
        
        // Créer une visualisation de menace
        const node = this.blockchainNodes.get(chain);
        if (!node) return;
        
        // Couleur basée sur la sévérité
        let color;
        switch (severity) {
            case 'low':
                color = 0xffff00;
                break;
            case 'medium':
                color = 0xff8800;
                break;
            case 'high':
                color = 0xff0000;
                break;
            case 'critical':
                color = 0xff00ff;
                break;
        }
        
        // Créer un effet de particules
        const particleCount = 100;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            const radius = Math.random() * 5 + 2;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;
            
            positions[i * 3] = node.position.x + radius * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = node.position.y + radius * Math.cos(phi);
            positions[i * 3 + 2] = node.position.z + radius * Math.sin(phi) * Math.sin(theta);
            
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
        });
        
        const particles = new THREE.Points(geometry, material);
        particles.userData = {
            type: 'threat',
            chain,
            severity,
            createdAt: Date.now(),
            lifespan: 5000, // 5 secondes
        };
        
        this.scene.add(particles);
        this.threatVisualizations.set(particles.uuid, particles);
        
        // Afficher une alerte dans l'interface
        this.showAlert(description, severity);
        
        // Supprimer après la durée de vie
        setTimeout(() => {
            this.scene.remove(particles);
            this.threatVisualizations.delete(particles.uuid);
        }, 5000);
    }
    
    showAlert(message, severity) {
        // Créer un élément d'alerte
        const alertDiv = document.createElement('div');
        alertDiv.className = `war-room-alert alert-${severity}`;
        alertDiv.innerHTML = `
            <div class="alert-header">
                <span class="alert-icon">⚠️</span>
                <span class="alert-title">${severity.toUpperCase()} ALERT</span>
                <span class="alert-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="alert-message">${message}</div>
        `;
        
        // Ajouter au conteneur d'alertes
        const alertContainer = document.getElementById('alert-container');
        if (alertContainer) {
            alertContainer.appendChild(alertDiv);
            
            // Supprimer après 10 secondes
            setTimeout(() => {
                alertDiv.remove();
            }, 10000);
        }
    }
    
    updateAgentActivity(activityData) {
        // Mettre à jour la visualisation des agents
        const { agent_id, action, chain, timestamp } = activityData;
        
        // Créer ou mettre à jour un avatar d'agent
        if (!this.agentAvatars.has(agent_id)) {
            this.createAgentAvatar(agent_id);
        }
        
        const avatar = this.agentAvatars.get(agent_id);
        
        // Déplacer l'avatar vers la chaîne concernée
        const targetNode = this.blockchainNodes.get(chain);
        if (targetNode) {
            this.moveAgentToChain(avatar, targetNode.position);
        }
        
        // Afficher l'action
        this.showAgentAction(agent_id, action);
    }
    
    createAgentAvatar(agentId) {
        // Créer un avatar sphérique pour l'agent
        const geometry = new THREE.SphereGeometry(0.5, 16, 16);
        const material = new THREE.MeshPhongMaterial({
            color: 0x00ff00,
            shininess: 30,
            emissive: 0x00ff00,
            emissiveIntensity: 0.3,
        });
        
        const avatar = new THREE.Mesh(geometry, material);
        
        // Position aléatoire initiale
        avatar.position.set(
            (Math.random() - 0.5) * 20,
            5,
            (Math.random() - 0.5) * 20
        );
        
        avatar.userData = {
            agentId,
            type: 'agent',
            speed: 0.05,
            targetPosition: null,
        };
        
        this.scene.add(avatar);
        this.agentAvatars.set(agentId, avatar);
        
        return avatar;
    }
    
    moveAgentToChain(avatar, targetPosition) {
        avatar.userData.targetPosition = new THREE.Vector3(
            targetPosition.x,
            targetPosition.y + 3,
            targetPosition.z
        );
    }
    
    showAgentAction(agentId, action) {
        // Afficher l'action dans le panneau d'activité
        const activityPanel = document.getElementById('agent-activity-panel');
        if (activityPanel) {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';
            activityItem.innerHTML = `
                <span class="activity-time">${new Date().toLocaleTimeString()}</span>
                <span class="activity-agent">Agent ${agentId.substring(0, 8)}</span>
                <span class="activity-action">${action}</span>
            `;
            
            activityPanel.appendChild(activityItem);
            
            // Garder seulement les 20 dernières activités
            const items = activityPanel.querySelectorAll('.activity-item');
            if (items.length > 20) {
                items[0].remove();
            }
        }
    }
    
    showTransactionAlert(transactionData) {
        const { hash, from, to, value, chain } = transactionData;
        
        // Créer une ligne de transaction animée
        const fromNode = this.blockchainNodes.get(chain);
        const toNode = this.blockchainNodes.get('ethereum'); // Pour l'exemple
        
        if (fromNode && toNode) {
            this.createTransactionBeam(fromNode.position, toNode.position, value);
        }
        
        // Afficher les détails
        this.showTransactionDetails(transactionData);
    }
    
    createTransactionBeam(fromPos, toPos, value) {
        // Créer un faisceau laser pour la transaction
        const direction = new THREE.Vector3().subVectors(toPos, fromPos).normalize();
        const distance = fromPos.distanceTo(toPos);
        
        const geometry = new THREE.CylinderGeometry(0.1, 0.1, distance, 8);
        geometry.rotateZ(Math.PI / 2);
        
        const material = new THREE.MeshBasicMaterial({
            color: 0x00ffff,
            transparent: true,
            opacity: 0.8,
        });
        
        const beam = new THREE.Mesh(geometry, material);
        
        // Positionner au milieu
        const midPoint = new THREE.Vector3().addVectors(fromPos, toPos).multiplyScalar(0.5);
        beam.position.copy(midPoint);
        
        // Orienter vers la cible
        beam.lookAt(toPos);
        
        this.scene.add(beam);
        
        // Animer et supprimer
        let opacity = 0.8;
        const animate = () => {
            opacity -= 0.02;
            material.opacity = opacity;
            
            if (opacity > 0) {
                requestAnimationFrame(animate);
            } else {
                this.scene.remove(beam);
            }
        };
        
        setTimeout(animate, 100);
    }
    
    showTransactionDetails(transactionData) {
        const detailsPanel = document.getElementById('transaction-details-panel');
        if (detailsPanel) {
            detailsPanel.innerHTML = `
                <div class="transaction-header">
                    <h3>Transaction Alert</h3>
                    <span class="transaction-chain">${transactionData.chain.toUpperCase()}</span>
                </div>
                <div class="transaction-details">
                    <div class="detail-row">
                        <span class="detail-label">Hash:</span>
                        <span class="detail-value">${transactionData.hash.substring(0, 16)}...</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">From:</span>
                        <span class="detail-value">${transactionData.from.substring(0, 12)}...</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">To:</span>
                        <span class="detail-value">${transactionData.to.substring(0, 12)}...</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Value:</span>
                        <span class="detail-value">${transactionData.value} ETH</span>
                    </div>
                </div>
            `;
            
            // Afficher le panneau
            detailsPanel.style.display = 'block';
            
            // Masquer après 10 secondes
            setTimeout(() => {
                detailsPanel.style.display = 'none';
            }, 10000);
        }
    }
    
    updateDashboard() {
        // Mettre à jour les statistiques du dashboard
        const statsContainer = document.getElementById('system-stats');
        if (!statsContainer) return;
        
        let totalThreats = 0;
        let healthyChains = 0;
        let warningChains = 0;
        let criticalChains = 0;
        
        Object.values(this.systemStatus).forEach(status => {
            totalThreats += status.threats;
            
            switch (status.status) {
                case 'healthy':
                    healthyChains++;
                    break;
                case 'warning':
                    warningChains++;
                    break;
                case 'critical':
                    criticalChains++;
                    break;
            }
        });
        
        statsContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${totalThreats}</div>
                <div class="stat-label">Threats Active</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${healthyChains}</div>
                <div class="stat-label">Healthy Chains</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${warningChains}</div>
                <div class="stat-label">Warning Chains</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${criticalChains}</div>
                <div class="stat-label">Critical Chains</div>
            </div>
        `;
    }
    
    // Méthodes de contrôle
    setAutoRotate(enabled) {
        this.controls.autoRotate = enabled;
    }
    
    setAnimationSpeed(speed) {
        this.config.animationSpeed = speed;
    }
    
    showLabels(show) {
        this.config.showLabels = show;
        
        this.blockchainNodes.forEach((node, chain) => {
            // Supprimer les labels existants
            node.children.forEach(child => {
                if (child.type === 'Sprite') {
                    node.remove(child);
                }
            });
            
            // Ajouter les nouveaux labels si nécessaire
            if (show) {
                this.addLabel(node, chain);
            }
        });
    }
    
    resetView() {
        this.controls.reset();
        this.camera.position.set(0, 20, 30);
    }
    
    // Méthodes de débogage
    logSceneInfo() {
        console.log('Scene Info:');
        console.log(`- Nodes: ${this.blockchainNodes.size}`);
        console.log(`- Agents: ${this.agentAvatars.size}`);
        console.log(`- Threats: ${this.threatVisualizations.size}`);
        console.log(`- Data Streams: ${this.dataStreams.size}`);
        
        console.log('System Status:');
        Object.entries(this.systemStatus).forEach(([chain, status]) => {
            console.log(`- ${chain}: ${status.status} (${status.threats} threats)`);
        });
    }
}

// Initialisation globale
let warRoom = null;

document.addEventListener('DOMContentLoaded', () => {
    warRoom = new WarRoom3D('war-room-container');
    
    // Exposer globalement pour le débogage
    window.warRoom = warRoom;
    
    // Contrôles de l'interface
    setupControls();
});

function setupControls() {
    // Auto-rotation
    const autoRotateToggle = document.getElementById('auto-rotate-toggle');
    if (autoRotateToggle) {
        autoRotateToggle.addEventListener('change', (e) => {
            warRoom.setAutoRotate(e.target.checked);
        });
    }
    
    // Vitesse d'animation
    const speedSlider = document.getElementById('animation-speed-slider');
    if (speedSlider) {
        speedSlider.addEventListener('input', (e) => {
            warRoom.setAnimationSpeed(parseFloat(e.target.value));
        });
    }
    
    // Labels
    const labelsToggle = document.getElementById('labels-toggle');
    if (labelsToggle) {
        labelsToggle.addEventListener('change', (e) => {
            warRoom.showLabels(e.target.checked);
        });
    }
    
    // Réinitialiser la vue
    const resetViewBtn = document.getElementById('reset-view-btn');
    if (resetViewBtn) {
        resetViewBtn.addEventListener('click', () => {
            warRoom.resetView();
        });
    }
    
    // Mode plein écran
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', () => {
            const container = document.getElementById('war-room-container');
            if (container.requestFullscreen) {
                container.requestFullscreen();
            } else if (container.webkitRequestFullscreen) {
                container.webkitRequestFullscreen();
            } else if (container.msRequestFullscreen) {
                container.msRequestFullscreen();
            }
        });
    }
}

// Simulation de données pour le développement
function simulateData() {
    if (!warRoom) return;
    
    // Simuler des changements de statut
    const chains = Object.keys(warRoom.systemStatus);
    const randomChain = chains[Math.floor(Math.random() * chains.length)];
    
    const statuses = ['healthy', 'warning', 'critical'];
    const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
    
    const threats = randomStatus === 'healthy' ? 0 : Math.floor(Math.random() * 5);
    
    warRoom.updateSystemStatus({
        ...warRoom.systemStatus,
        [randomChain]: { status: randomStatus, threats }
    });
    
    // Simuler une menace occasionnelle
    if (Math.random() < 0.3) {
        const severities = ['low', 'medium', 'high', 'critical'];
        const randomSeverity = severities[Math.floor(Math.random() * severities.length)];
        
        warRoom.visualizeThreat({
            chain: randomChain,
            severity: randomSeverity,
            description: `Simulated ${randomSeverity} threat on ${randomChain}`,
            transaction_hash: '0x' + Math.random().toString(16).substring(2, 10),
        });
    }
    
    // Simuler une activité d'agent
    if (Math.random() < 0.4) {
        const actions = ['Transaction executed', 'Contract deployed', 'Token swapped', 'Liquidity added'];
        const randomAction = actions[Math.floor(Math.random() * actions.length)];
        
        warRoom.updateAgentActivity({
            agent_id: 'agent_' + Math.floor(Math.random() * 1000),
            action: randomAction,
            chain: randomChain,
            timestamp: Date.now(),
        });
    }
}

// Démarrer la simulation si en mode développement
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    setInterval(simulateData, 5000);
}
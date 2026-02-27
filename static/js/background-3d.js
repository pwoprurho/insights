/**
 * Insight Collective - Robotic "Clarity from Confusion" 3D Background
 * Sequenced Animation: Reach -> Gather -> Join -> Reset
 */

class RoboticInsight {
    constructor() {
        this.container = document.getElementById('bg-canvas');
        if (!this.container) return;

        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2500);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

        this.strings = [];
        this.stringCount = 35;
        this.mouse = new THREE.Vector2(0, 0);
        this.clock = new THREE.Clock();

        // Animation States: 0: REACH, 1: GATHER, 2: JOIN, 3: RESET
        this.state = 0;
        this.stateTimer = 0;
        this.durations = [3, 4, 2, 2]; // Seconds for each state

        this.init();
    }

    init() {
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        this.camera.position.z = 800;

        // Lighting
        const mainLight = new THREE.PointLight(0x02AFF1, 2, 1500);
        mainLight.position.set(0, 200, 300);
        this.scene.add(mainLight);

        const ambientLight = new THREE.AmbientLight(0x404040, 1.5);
        this.scene.add(ambientLight);

        // --- Create Robot ---
        this.robotGroup = new THREE.Group();
        const robotMat = new THREE.MeshPhongMaterial({ color: 0x23265c, shininess: 80 });

        // Head
        this.head = new THREE.Mesh(new THREE.BoxGeometry(50, 50, 50), robotMat);
        this.head.position.y = 120;
        this.robotGroup.add(this.head);

        // Eyes
        const eyeMat = new THREE.MeshBasicMaterial({ color: 0x02AFF1 });
        const eyeL = new THREE.Mesh(new THREE.SphereGeometry(5), eyeMat);
        eyeL.position.set(-15, 125, 25);
        const eyeR = new THREE.Mesh(new THREE.SphereGeometry(5), eyeMat);
        eyeR.position.set(15, 125, 25);
        this.robotGroup.add(eyeL, eyeR);

        // Torso
        this.torso = new THREE.Mesh(new THREE.BoxGeometry(100, 140, 60), robotMat);
        this.robotGroup.add(this.torso);

        // Arms (Simplified - No Elbow)
        this.leftArm = this.createArm(-60, 40, robotMat);
        this.rightArm = this.createArm(60, 40, robotMat);
        this.robotGroup.add(this.leftArm.group, this.rightArm.group);

        this.scene.add(this.robotGroup);

        // --- Insight Point (Above Head) ---
        this.insightPoint = new THREE.Mesh(
            new THREE.SphereGeometry(20, 32, 32),
            new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 })
        );
        this.insightPoint.position.set(0, 300, 50);
        this.scene.add(this.insightPoint);

        this.insightGlow = new THREE.Mesh(
            new THREE.SphereGeometry(45, 32, 32),
            new THREE.MeshBasicMaterial({ color: 0x02AFF1, transparent: true, opacity: 0 })
        );
        this.insightGlow.position.copy(this.insightPoint.position);
        this.scene.add(this.insightGlow);

        // --- Strings ---
        this.createStrings();

        window.addEventListener('resize', () => this.onWindowResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));

        this.animate();
    }

    createArm(x, y, material) {
        const group = new THREE.Group();
        group.position.set(0, 40, 0); // Pivot from the nucleus (Torso center)

        const shoulder = new THREE.Mesh(new THREE.SphereGeometry(15), material);
        shoulder.position.set(x, 0, 0); // Offset shoulder from center
        group.add(shoulder);

        const arm = new THREE.Mesh(new THREE.CylinderGeometry(10, 8, 150), material);
        arm.position.set(x, 75, 0);

        const hand = new THREE.Mesh(new THREE.SphereGeometry(12), material);
        hand.position.set(x, 150, 0);
        group.add(arm);
        group.add(hand);

        return { group, hand };
    }

    createStrings() {
        const material = new THREE.LineBasicMaterial({
            color: 0x02AFF1,
            transparent: true,
            opacity: 0.3
        });

        for (let i = 0; i < this.stringCount; i++) {
            const start = new THREE.Vector3(
                (Math.random() - 0.5) * 2500,
                (Math.random() - 0.5) * 2500,
                (Math.random() - 1) * 1200
            );

            const geometry = new THREE.BufferGeometry().setFromPoints([start, start, start]);
            const line = new THREE.Line(geometry, material.clone());
            this.scene.add(line);

            this.strings.push({
                line,
                start,
                currentEnd: start.clone(),
                targetEnd: start.clone(),
                phase: Math.random() * Math.PI * 2
            });
        }
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    onMouseMove(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        const delta = this.clock.getDelta();
        const time = this.clock.getElapsedTime();
        this.stateTimer += delta;

        // State Switching Logic
        if (this.stateTimer > this.durations[this.state]) {
            this.state = (this.state + 1) % 4;
            this.stateTimer = 0;
        }

        const progress = this.stateTimer / this.durations[this.state];
        const worldHandL = new THREE.Vector3();
        const worldHandR = new THREE.Vector3();
        this.leftArm.hand.getWorldPosition(worldHandL);
        this.rightArm.hand.getWorldPosition(worldHandR);

        // --- State Specific Animations ---
        switch (this.state) {
            case 0: // REACH - Start Top (0), reach out in nuclear arc
                this.leftArm.group.rotation.z = THREE.MathUtils.lerp(0, Math.PI / 1.5, progress);
                this.rightArm.group.rotation.z = THREE.MathUtils.lerp(0, -Math.PI / 1.5, progress);

                this.insightPoint.material.opacity = Math.max(0, this.insightPoint.material.opacity - 0.2);
                this.insightGlow.material.opacity = Math.max(0, this.insightGlow.material.opacity - 0.2);
                break;

            case 1: // GATHER - Sweep back into Top from the sides
                this.leftArm.group.rotation.z = THREE.MathUtils.lerp(Math.PI / 1.5, 0, progress);
                this.rightArm.group.rotation.z = THREE.MathUtils.lerp(-Math.PI / 1.5, 0, progress);
                break;

            case 2: // JOIN - Hands meet perfectly at the apex above head
                this.leftArm.group.rotation.z = 0;
                this.rightArm.group.rotation.z = 0;

                // Show Insight Point
                this.insightPoint.material.opacity = THREE.MathUtils.lerp(0, 1, progress);
                this.insightGlow.material.opacity = THREE.MathUtils.lerp(0, 0.6, progress);
                break;

            case 3: // RESET - Pause at the Nucleus
                this.leftArm.group.rotation.z = 0;
                this.rightArm.group.rotation.z = 0;
                break;
        }

        // --- Animate Strings ---
        this.strings.forEach((s, i) => {
            if (this.state === 1) { // GATHER
                // Target the closest hand
                const target = i % 2 === 0 ? worldHandL : worldHandR;
                s.targetEnd.lerp(target, 0.1);
            } else if (this.state === 2) { // JOIN
                s.targetEnd.lerp(this.insightPoint.position, 0.2);
            } else if (this.state === 3) { // RESET
                s.targetEnd.lerp(s.start, 0.05);
            } else { // REACH
                s.targetEnd.copy(s.start);
            }

            s.currentEnd.lerp(s.targetEnd, 0.1);

            // Update Line Geometry (Bezier Curve)
            const mid = new THREE.Vector3().lerpVectors(s.start, s.currentEnd, 0.5);
            mid.y += Math.sin(time + s.phase) * 100; // Adding "chaos" to the strings
            mid.x += Math.cos(time + s.phase) * 100;

            const curve = new THREE.QuadraticBezierCurve3(s.start, mid, s.currentEnd);
            s.line.geometry.setFromPoints(curve.getPoints(20));
        });

        // Robot Body Floating
        this.robotGroup.position.y = Math.sin(time * 0.4) * 30;
        this.robotGroup.rotation.y = this.mouse.x * 0.3;
        this.robotGroup.rotation.x = -this.mouse.y * 0.2;

        this.renderer.render(this.scene, this.camera);
    }
}

new RoboticInsight();

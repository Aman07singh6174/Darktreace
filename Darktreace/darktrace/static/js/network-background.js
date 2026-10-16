import * as THREE from "../vendor/three.module.min.js";

const canvas = document.getElementById("network-background");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const smallScreen = window.matchMedia("(max-width: 760px)").matches;
const lowPower = (navigator.hardwareConcurrency || 8) <= 4;

if (canvas && !smallScreen && !lowPower) {
    try {
        const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.35));
        renderer.setSize(window.innerWidth, window.innerHeight, false);
        renderer.setClearColor(0x000000, 0);
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
        camera.position.z = 22;
        const count = reducedMotion ? 24 : 42;
        const positions = new Float32Array(count * 3);
        const randoms = new Float32Array(count * 3);
        for (let index = 0; index < count; index += 1) {
            positions[index * 3] = (Math.random() - 0.5) * 27;
            positions[index * 3 + 1] = (Math.random() - 0.5) * 15;
            positions[index * 3 + 2] = (Math.random() - 0.5) * 8;
            randoms[index * 3] = positions[index * 3];
            randoms[index * 3 + 1] = positions[index * 3 + 1];
            randoms[index * 3 + 2] = positions[index * 3 + 2];
        }
        const pointGeometry = new THREE.BufferGeometry();
        pointGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        const points = new THREE.Points(pointGeometry, new THREE.PointsMaterial({ color: 0x9bcf83, size: 0.075, transparent: true, opacity: 0.48, sizeAttenuation: true }));
        scene.add(points);

        const linePositions = [];
        for (let left = 0; left < count; left += 1) {
            for (let right = left + 1; right < count; right += 1) {
                const dx = randoms[left * 3] - randoms[right * 3];
                const dy = randoms[left * 3 + 1] - randoms[right * 3 + 1];
                if (Math.hypot(dx, dy) < 4.2) {
                    linePositions.push(randoms[left * 3], randoms[left * 3 + 1], randoms[left * 3 + 2], randoms[right * 3], randoms[right * 3 + 1], randoms[right * 3 + 2]);
                }
            }
        }
        const lineGeometry = new THREE.BufferGeometry();
        lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));
        const lines = new THREE.LineSegments(lineGeometry, new THREE.LineBasicMaterial({ color: 0x5f9881, transparent: true, opacity: 0.19 }));
        scene.add(lines);

        const resize = () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight, false);
        };
        window.addEventListener("resize", resize, { passive: true });
        if (reducedMotion) {
            renderer.render(scene, camera);
        } else {
            let frame = 0;
            const animate = () => {
                if (document.hidden) {
                    window.setTimeout(animate, 1000);
                    return;
                }
                frame += 1;
                points.rotation.z = Math.sin(frame * 0.001) * 0.012;
                lines.rotation.z = points.rotation.z;
                renderer.render(scene, camera);
                window.requestAnimationFrame(animate);
            };
            window.requestAnimationFrame(animate);
        }
    } catch (error) {
        canvas.hidden = true;
        console.info("Decorative network background unavailable; dashboard remains fully usable.", error.message);
    }
}
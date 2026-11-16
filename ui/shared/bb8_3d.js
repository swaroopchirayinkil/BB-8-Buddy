/**
 * BB-8 3D Desktop Character for BB-8 Buddy.
 * Built with Three.js from bb_8_3d_desktop_character_demo.html:
 * - High-detail procedural textures for body (6 medallions) & dome head (teal crown, orange stripe)
 * - Stabilized dome head hierarchy with primary photoreceptor eye, glowing ring, and specular glint
 * - Secondary holoprojector eye with volumetric cyan hologram beam & point light
 * - Dual whip antennas & magnetic neck collar with roller bearings
 * - Holographic docking pad
 * - 5 Interactive Moods: Idle, Excited, Patrol Roll (kinematics), Curious, Hologram
 * - Web Audio API procedural droid sound synthesizer
 * - Mouse look tracking & click raycasting
 */

class DroidAudioEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  ensureContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  setEnabled(val) {
    this.enabled = Boolean(val);
  }

  playSuccess() {
    this.playChirp('happy');
  }

  playBreak() {
    this.playChirp('curious');
  }

  playKeyClick() {
    if (!this.enabled) return;
    try {
      this.ensureContext();
      if (!this.ctx) return;
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(1200 + Math.random() * 400, now);
      gain.gain.setValueAtTime(0.03, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.02);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.025);
    } catch (e) {}
  }

  playRecBeep(isStart = true) {
    this.playChirp(isStart ? 'hologram' : 'idle');
  }

  playChirp(type = 'idle') {
    if (!this.enabled) return;
    try {
      this.ensureContext();
      if (!this.ctx) return;
      const now = this.ctx.currentTime;

      const patterns = {
        idle: [
          { f1: 780, f2: 1120, dur: 0.08, delay: 0 },
          { f1: 1180, f2: 920, dur: 0.09, delay: 0.10 }
        ],
        happy: [
          { f1: 680, f2: 1450, dur: 0.07, delay: 0 },
          { f1: 1200, f2: 1950, dur: 0.08, delay: 0.08 },
          { f1: 1500, f2: 2300, dur: 0.11, delay: 0.17 },
          { f1: 1850, f2: 1350, dur: 0.09, delay: 0.30 }
        ],
        curious: [
          { f1: 540, f2: 960, dur: 0.16, delay: 0 },
          { f1: 880, f2: 1380, dur: 0.18, delay: 0.20 }
        ],
        patrol: [
          { f1: 420, f2: 880, dur: 0.06, delay: 0 },
          { f1: 720, f2: 1150, dur: 0.07, delay: 0.08 },
          { f1: 950, f2: 640, dur: 0.07, delay: 0.17 }
        ],
        hologram: [
          { f1: 320, f2: 980, dur: 0.22, delay: 0 },
          { f1: 980, f2: 1420, dur: 0.25, delay: 0.22 }
        ]
      };

      const notes = patterns[type] || patterns.idle;
      notes.forEach((n) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';

        const start = now + n.delay;
        const end = start + n.dur;

        osc.frequency.setValueAtTime(n.f1, start);
        osc.frequency.exponentialRampToValueAtTime(Math.max(80, n.f2), end);

        gain.gain.setValueAtTime(0.001, start);
        gain.gain.linearRampToValueAtTime(0.12, start + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.001, end);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(start);
        osc.stop(end + 0.01);
      });
    } catch (e) {
      // Ignore audio initialization errors
    }
  }
}

class BB8_3D {
  constructor(canvasOrContainer, options = {}) {
    this.options = Object.assign({
      width: 250,
      height: 175,
      onClick: null,
      onMoodChange: null,
      defaultMood: 'idle',
      characterSize: 'small',
      enableAudio: true,
      showDockPad: true,
    }, options);

    this.isCanvas = canvasOrContainer instanceof HTMLCanvasElement;
    this.canvas = this.isCanvas ? canvasOrContainer : null;
    this.container = this.isCanvas ? canvasOrContainer.parentElement : canvasOrContainer;

    this.width = this.options.width;
    this.height = this.options.height;

    this.currentMood = this.options.defaultMood || 'idle';
    this.characterScale = this._parseScale(this.options.characterSize);
    this.audioEngine = new DroidAudioEngine();
    this.audioEngine.enabled = this.options.enableAudio !== false;
    if (!window.bb8Audio) {
      window.bb8Audio = this.audioEngine;
    }

    this.BODY_RADIUS = 1.25;
    this.HEAD_RADIUS = 0.74;

    this.targetLook = { x: 0, y: 0 };
    this.smoothLook = { x: 0, y: 0 };
    this.isLookingUp = false;
    this.patrolAngle = 0;
    this.excitedBounceTime = 0;
    this.clock = null;

    if (window.THREE) {
      this._initThreeJS();
    } else {
      console.warn('[BB-8 3D] Three.js not loaded, using fallback');
      this._init2DFallback();
    }
  }

  /* ==========================================================
     Procedural Textures for BB-8 Body & Dome Head
     ========================================================== */

  _createBodyTexture() {
    const THREE = window.THREE;
    const width = 1024;
    const height = 512;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    // Base warm off-white ceramic hull (#F4F1EA)
    ctx.fillStyle = '#f4f1ea';
    ctx.fillRect(0, 0, width, height);

    // Seam lines connecting medallions
    ctx.strokeStyle = '#8b8a84';
    ctx.lineWidth = 3;

    ctx.beginPath();
    ctx.moveTo(0, height * 0.5);
    ctx.lineTo(width, height * 0.5);
    ctx.stroke();

    [0.125, 0.375, 0.625, 0.875].forEach((u) => {
      ctx.beginPath();
      ctx.moveTo(width * u, 0);
      ctx.lineTo(width * u, height);
      ctx.stroke();
    });

    // 6 Tangerine-orange circular medallions
    const medallionCenters = [
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(0, 0, -1),
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(-1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, -1, 0)
    ];

    const imgData = ctx.getImageData(0, 0, width, height);
    const data = imgData.data;
    const maxAngle = 0.56;

    for (let py = 0; py < height; py++) {
      const v = 1 - py / height;
      const theta = (1 - v) * Math.PI;
      const sinTheta = Math.sin(theta);
      const cosTheta = Math.cos(theta);

      for (let px = 0; px < width; px++) {
        const u = px / width;
        const phi = u * Math.PI * 2;

        const sx = -sinTheta * Math.cos(phi);
        const sy = cosTheta;
        const sz = sinTheta * Math.sin(phi);

        for (let m = 0; m < medallionCenters.length; m++) {
          const c = medallionCenters[m];
          const dot = Math.max(-1, Math.min(1, sx * c.x + sy * c.y + sz * c.z));
          const angDist = Math.acos(dot);

          if (angDist <= maxAngle) {
            const rNorm = angDist / maxAngle;

            let tx = 0, ty = 0;
            if (Math.abs(c.y) > 0.9) {
              tx = sx;
              ty = sz * c.y;
            } else {
              tx = -sx * c.z + sz * c.x;
              ty = sy;
            }
            const localAngle = Math.atan2(ty, tx);

            let color = null;

            if (rNorm > 0.96 && rNorm <= 1.0) {
              color = [217, 78, 0]; // Outer border
            } else if (rNorm > 0.66 && rNorm <= 0.96) {
              color = rNorm > 0.89 ? [255, 140, 26] : [255, 107, 0]; // Tangerine orange ring
            } else if (rNorm > 0.625 && rNorm <= 0.66) {
              color = [217, 78, 0];
            } else if (rNorm <= 0.625) {
              const spokeAngle = ((localAngle + Math.PI / 4) % (Math.PI / 2) + (Math.PI / 2)) % (Math.PI / 2) - Math.PI / 4;
              const isSpoke = Math.abs(spokeAngle) < 0.23 && rNorm > 0.34;
              const isTBarCap = Math.abs(spokeAngle) < 0.34 && rNorm > 0.34 && rNorm < 0.41;

              if (isSpoke || isTBarCap) {
                color = [255, 119, 0]; // Inner orange tabs
              } else if (rNorm < 0.22) {
                color = [110, 114, 120]; // Hub core
              } else if (rNorm >= 0.22 && rNorm < 0.255) {
                color = [68, 71, 77];
              } else {
                const plateSeg = Math.floor(((localAngle + Math.PI) / (Math.PI * 2)) * 8);
                color = (plateSeg % 2 === 0 && rNorm > 0.32 && rNorm < 0.58) ? [122, 120, 114] : [238, 234, 225];
              }
            }

            if (color) {
              const idx = (py * width + px) * 4;
              data[idx] = color[0];
              data[idx + 1] = color[1];
              data[idx + 2] = color[2];
              data[idx + 3] = 255;
            }
            break;
          }
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Add rivets
    const rivetCoords = [
      [0.125, 0.32], [0.125, 0.68],
      [0.375, 0.32], [0.375, 0.68],
      [0.625, 0.32], [0.625, 0.68],
      [0.875, 0.32], [0.875, 0.68]
    ];

    rivetCoords.forEach(([u, v]) => {
      const cx = u * width;
      const cy = v * height;
      ctx.beginPath();
      ctx.arc(cx, cy, 7, 0, Math.PI * 2);
      ctx.fillStyle = '#9c988e';
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#6c6961';
      ctx.stroke();
    });

    const texture = new THREE.CanvasTexture(canvas);
    texture.anisotropy = 4;
    return texture;
  }

  _createHeadTexture() {
    const THREE = window.THREE;
    const width = 1024;
    const height = 512;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    // Base warm off-white dome (#F4F1EA)
    ctx.fillStyle = '#f4f1ea';
    ctx.fillRect(0, 0, width, height);

    // Top crown cap in crisp teal-blue (#1C7C9C)
    ctx.fillStyle = '#1c7c9c';
    ctx.fillRect(0, 0, width, height * 0.15);

    ctx.fillStyle = '#145a73';
    ctx.fillRect(0, height * 0.15, width, 5);

    // Upper vivid tangerine-orange accent stripe (#FF6B00)
    ctx.fillStyle = '#ff6b00';
    ctx.fillRect(0, height * 0.23, width, 28);
    ctx.strokeStyle = '#d94e00';
    ctx.lineWidth = 2.5;
    ctx.strokeRect(0, height * 0.23, width, 28);

    // Photoreceptor eye clear surround
    ctx.fillStyle = '#f4f1ea';
    ctx.fillRect(width * 0.15, height * 0.20, width * 0.20, height * 0.54);

    // Lower detail blocks (#FF7700)
    const blockPositions = [0.03, 0.085, 0.41, 0.47, 0.61, 0.77, 0.90];
    blockPositions.forEach((u) => {
      ctx.fillStyle = '#ff7700';
      ctx.fillRect(width * u, height * 0.67, 36, 24);
      ctx.strokeStyle = '#d94e00';
      ctx.lineWidth = 2.5;
      ctx.strokeRect(width * u, height * 0.67, 36, 24);
    });

    // Lower teal-blue band (#1C7C9C)
    ctx.fillStyle = '#1c7c9c';
    ctx.fillRect(0, height * 0.81, width, height * 0.085);

    // Rim trim
    ctx.fillStyle = '#c4bfb4';
    ctx.fillRect(0, height * 0.895, width, height * 0.105);

    const texture = new THREE.CanvasTexture(canvas);
    texture.anisotropy = 4;
    return texture;
  }

  /* ==========================================================
     Three.js Scene & Droid Character Assembly
     ========================================================== */

  _initThreeJS() {
    const THREE = window.THREE;
    const w = this.width;
    const h = this.height;

    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(35, w / h, 0.1, 50);
    this.camera.position.set(0, 1.62, 6.4);
    this.camera.lookAt(0, 1.50, 0);

    const rendererOptions = {
      antialias: true,
      alpha: true,
      premultipliedAlpha: true
    };
    if (this.canvas) {
      rendererOptions.canvas = this.canvas;
    }

    this.renderer = new THREE.WebGLRenderer(rendererOptions);
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;

    if (!this.isCanvas && this.container) {
      this.container.appendChild(this.renderer.domElement);
      this.canvas = this.renderer.domElement;
    }

    this.canvas.style.backgroundColor = 'transparent';
    this.canvas.style.cursor = 'pointer';

    // Three-point Lighting
    this.ambientLight = new THREE.HemisphereLight(0xfff5eb, 0x3b2618, 0.95);
    this.scene.add(this.ambientLight);

    this.keyLight = new THREE.DirectionalLight(0xfff1e0, 1.35);
    this.keyLight.position.set(4.0, 6.5, 5.0);
    this.scene.add(this.keyLight);

    this.rimLight = new THREE.DirectionalLight(0xff6b00, 0.95);
    this.rimLight.position.set(-4.0, 3.5, -3.8);
    this.scene.add(this.rimLight);

    this.fillLight = new THREE.DirectionalLight(0xffb366, 0.5);
    this.fillLight.position.set(-3.5, 2.0, 3.8);
    this.scene.add(this.fillLight);

    // Holographic Dock Pad
    this.dockPadGroup = new THREE.Group();
    this.scene.add(this.dockPadGroup);

    const padOuterGeo = new THREE.RingGeometry(1.35, 1.44, 48);
    padOuterGeo.rotateX(-Math.PI / 2);
    const padOuterMat = new THREE.MeshBasicMaterial({
      color: 0xff6b00,
      transparent: true,
      opacity: 0.65,
      side: THREE.DoubleSide
    });
    const padOuter = new THREE.Mesh(padOuterGeo, padOuterMat);
    padOuter.position.y = 0.005;
    this.dockPadGroup.add(padOuter);

    const padInnerGeo = new THREE.RingGeometry(0.88, 0.92, 48);
    padInnerGeo.rotateX(-Math.PI / 2);
    const padInnerMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide
    });
    const padInner = new THREE.Mesh(padInnerGeo, padInnerMat);
    padInner.position.y = 0.005;
    this.dockPadGroup.add(padInner);
    this.dockPadGroup.visible = this.options.showDockPad !== false;

    // Build BB-8 Character Hierarchy
    this._buildCharacter();

    // Event Listeners
    this._setupInteractions();

    // Start Animation Loop
    this.clock = new THREE.Clock();
    this.start();
  }

  _buildCharacter() {
    const THREE = window.THREE;
    this.bb8Root = new THREE.Group();
    this.bb8Root.scale.set(this.characterScale, this.characterScale, this.characterScale);
    this.scene.add(this.bb8Root);

    // 1. Spherical Rolling Body
    const bodyGeo = new THREE.SphereGeometry(this.BODY_RADIUS, 48, 36);
    const bodyTex = this._createBodyTexture();
    const bodyMat = new THREE.MeshStandardMaterial({
      map: bodyTex,
      roughness: 0.32,
      metalness: 0.08
    });
    this.bodySphere = new THREE.Mesh(bodyGeo, bodyMat);
    this.bodySphere.position.y = this.BODY_RADIUS;
    this.bb8Root.add(this.bodySphere);

    // 2. Stabilized Dome Head Hierarchy
    this.headPivotGroup = new THREE.Group();
    this.headPivotGroup.position.y = this.BODY_RADIUS;
    this.bb8Root.add(this.headPivotGroup);

    this.headTiltGroup = new THREE.Group();
    this.headPivotGroup.add(this.headTiltGroup);

    this.headSpinGroup = new THREE.Group();
    this.headSpinGroup.position.y = this.BODY_RADIUS - 0.02;
    this.headTiltGroup.add(this.headSpinGroup);

    // Lower Neck Collar
    const collarGeo = new THREE.CylinderGeometry(this.HEAD_RADIUS * 0.99, this.HEAD_RADIUS * 0.83, 0.16, 36);
    const collarMat = new THREE.MeshStandardMaterial({
      color: 0xc2bdb2,
      roughness: 0.38,
      metalness: 0.25
    });
    const collarMesh = new THREE.Mesh(collarGeo, collarMat);
    collarMesh.position.y = 0.08;
    this.headSpinGroup.add(collarMesh);

    // Neck Gasket
    const gasketGeo = new THREE.CylinderGeometry(this.HEAD_RADIUS * 0.82, this.HEAD_RADIUS * 0.76, 0.05, 36);
    const gasketMat = new THREE.MeshStandardMaterial({
      color: 0x262930,
      roughness: 0.6,
      metalness: 0.45
    });
    const gasketMesh = new THREE.Mesh(gasketGeo, gasketMat);
    gasketMesh.position.y = 0.01;
    this.headSpinGroup.add(gasketMesh);

    // Roller Bearings
    const bearingGeo = new THREE.SphereGeometry(0.026, 8, 8);
    const bearingMat = new THREE.MeshStandardMaterial({
      color: 0xff7700,
      roughness: 0.25,
      metalness: 0.75
    });
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2;
      const bearing = new THREE.Mesh(bearingGeo, bearingMat);
      bearing.position.set(
        Math.cos(angle) * (this.HEAD_RADIUS * 0.79),
        0.005,
        Math.sin(angle) * (this.HEAD_RADIUS * 0.79)
      );
      this.headSpinGroup.add(bearing);
    }

    // Dome Head
    const domeGeo = new THREE.SphereGeometry(this.HEAD_RADIUS, 36, 24, 0, Math.PI * 2, 0, Math.PI * 0.5);
    const domeTex = this._createHeadTexture();
    const domeMat = new THREE.MeshStandardMaterial({
      map: domeTex,
      roughness: 0.28,
      metalness: 0.10
    });
    const domeMesh = new THREE.Mesh(domeGeo, domeMat);
    domeMesh.position.y = 0.14;
    this.headSpinGroup.add(domeMesh);

    // 3. Primary Photoreceptor Eye (Front +Z)
    const eyeHousing = new THREE.Group();
    eyeHousing.position.set(0, 0.14 + this.HEAD_RADIUS * 0.45, this.HEAD_RADIUS * 0.88);
    eyeHousing.rotation.x = -0.38;
    this.headSpinGroup.add(eyeHousing);

    const bezelGeo = new THREE.CylinderGeometry(0.18, 0.20, 0.08, 24);
    bezelGeo.rotateX(Math.PI / 2);
    const bezelMat = new THREE.MeshStandardMaterial({
      color: 0x262930,
      roughness: 0.3,
      metalness: 0.7
    });
    const bezelMesh = new THREE.Mesh(bezelGeo, bezelMat);
    eyeHousing.add(bezelMesh);

    // Glowing Orange Accent Ring
    const eyeRingGeo = new THREE.TorusGeometry(0.165, 0.014, 12, 24);
    const eyeRingMat = new THREE.MeshStandardMaterial({
      color: 0xff6b00,
      emissive: 0xff5500,
      emissiveIntensity: 0.45,
      roughness: 0.25
    });
    const eyeRing = new THREE.Mesh(eyeRingGeo, eyeRingMat);
    eyeRing.position.z = 0.036;
    eyeHousing.add(eyeRing);

    // Glossy Dark Photoreceptor Lens
    const lensGeo = new THREE.SphereGeometry(0.145, 18, 18);
    const lensMat = new THREE.MeshPhysicalMaterial({
      color: 0x090d16,
      roughness: 0.06,
      metalness: 0.1,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05
    });
    const lensMesh = new THREE.Mesh(lensGeo, lensMat);
    lensMesh.scale.set(1, 1, 0.48);
    lensMesh.position.z = 0.025;
    eyeHousing.add(lensMesh);

    // Specular Catchlight Dot
    const glintGeo = new THREE.SphereGeometry(0.026, 8, 8);
    const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const glintMesh = new THREE.Mesh(glintGeo, glintMat);
    glintMesh.position.set(-0.048, 0.048, 0.088);
    eyeHousing.add(glintMesh);

    // 4. Secondary Holoprojector Eye
    const holoGroup = new THREE.Group();
    holoGroup.position.set(0.28, 0.14 + this.HEAD_RADIUS * 0.34, this.HEAD_RADIUS * 0.85);
    holoGroup.rotation.set(-0.28, 0.34, 0);
    this.headSpinGroup.add(holoGroup);

    const holoRimGeo = new THREE.CylinderGeometry(0.082, 0.09, 0.06, 18);
    holoRimGeo.rotateX(Math.PI / 2);
    const holoRimMesh = new THREE.Mesh(holoRimGeo, bezelMat);
    holoGroup.add(holoRimMesh);

    const holoLensGeo = new THREE.SphereGeometry(0.064, 14, 14);
    const holoLensMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      emissive: 0x38bdf8,
      emissiveIntensity: 0.25,
      roughness: 0.15
    });
    const holoLensMesh = new THREE.Mesh(holoLensGeo, holoLensMat);
    holoLensMesh.scale.set(1, 1, 0.5);
    holoLensMesh.position.z = 0.022;
    holoGroup.add(holoLensMesh);

    this.holoLensLight = new THREE.PointLight(0x38bdf8, 0, 4.0);
    this.holoLensLight.position.set(0, 0, 0.18);
    holoGroup.add(this.holoLensLight);

    // Volumetric Hologram Projection Beam
    const beamGeo = new THREE.ConeGeometry(0.75, 2.2, 24, 1, true);
    beamGeo.translate(0, -1.1, 0);
    beamGeo.rotateX(-Math.PI / 2);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    this.holoBeamMesh = new THREE.Mesh(beamGeo, beamMat);
    this.holoBeamMesh.position.z = 0.05;
    holoGroup.add(this.holoBeamMesh);

    // 5. Dual Whip Antennas
    const antBaseMat = new THREE.MeshStandardMaterial({
      color: 0xd6d1c7,
      roughness: 0.35,
      metalness: 0.6
    });
    const antTipMat = new THREE.MeshStandardMaterial({
      color: 0xff6b00,
      emissive: 0xff5500,
      emissiveIntensity: 0.35
    });

    const tallAntGeo = new THREE.CylinderGeometry(0.011, 0.018, 0.44, 8);
    const tallAnt = new THREE.Mesh(tallAntGeo, antBaseMat);
    tallAnt.position.set(-0.08, 0.14 + this.HEAD_RADIUS + 0.18, -0.06);
    this.headSpinGroup.add(tallAnt);

    const tallTip = new THREE.Mesh(new THREE.SphereGeometry(0.016, 8, 8), antTipMat);
    tallTip.position.set(-0.08, 0.14 + this.HEAD_RADIUS + 0.40, -0.06);
    this.headSpinGroup.add(tallTip);

    const shortAntGeo = new THREE.CylinderGeometry(0.009, 0.014, 0.26, 8);
    const shortAnt = new THREE.Mesh(shortAntGeo, antBaseMat);
    shortAnt.position.set(-0.17, 0.14 + this.HEAD_RADIUS + 0.10, -0.02);
    this.headSpinGroup.add(shortAnt);
  }

  _setupInteractions() {
    const THREE = window.THREE;

    // Mouse look tracking
    const updateTargetLook = (cx, cy) => {
      const rect = this.canvas.getBoundingClientRect();
      this.targetLook.x = ((cx - rect.left) / rect.width) * 2 - 1;
      this.targetLook.y = -(((cy - rect.top) / rect.height) * 2 - 1);
    };

    window.addEventListener('mousemove', (e) => {
      updateTargetLook(e.clientX, e.clientY);
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.targetLook.x = 0;
      this.targetLook.y = 0;
    });

    // Raycast click
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let downPos = { x: 0, y: 0 };

    this.canvas.addEventListener('mousedown', (e) => {
      downPos = { x: e.clientX, y: e.clientY };
    });

    this.canvas.addEventListener('click', (e) => {
      const dist = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
      if (dist > 8) return;

      const rect = this.canvas.getBoundingClientRect();
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);

      raycaster.setFromCamera(pointer, this.camera);
      const hits = raycaster.intersectObjects(this.bb8Root.children, true);

      // Trigger interaction
      this.triggerHop();
      if (typeof this.options.onClick === 'function') {
        this.options.onClick();
      }
    });
  }

  /* ==========================================================
     Animation API & Mood Control
     ========================================================== */

  _parseScale(val) {
    if (typeof val === 'number') return Math.max(0.4, Math.min(1.5, val));
    const map = {
      compact: 0.68,
      small: 0.80,
      medium: 0.95,
      large: 1.10
    };
    return map[val] || 0.80;
  }

  setScale(scaleOrSize) {
    this.characterScale = this._parseScale(scaleOrSize);
    if (this.bb8Root) {
      this.bb8Root.scale.set(this.characterScale, this.characterScale, this.characterScale);
    }
    if (this.dockPadGroup) {
      this.dockPadGroup.scale.set(this.characterScale, this.characterScale, this.characterScale);
    }
  }

  setMood(mood) {
    this.currentMood = mood;
    if (mood === 'happy') {
      this.excitedBounceTime = 1.6;
    }
    this.audioEngine.playChirp(mood);

    if (typeof this.options.onMoodChange === 'function') {
      this.options.onMoodChange(mood);
    }
  }

  triggerHop() {
    this.excitedBounceTime = 1.4;
    this.audioEngine.playChirp('happy');
  }

  setLookingUp(val) {
    this.isLookingUp = Boolean(val);
  }

  toggleDockPad(show) {
    if (typeof show === 'boolean') {
      this.dockPadGroup.visible = show;
    } else {
      this.dockPadGroup.visible = !this.dockPadGroup.visible;
    }
  }

  start() {
    const loop = () => {
      this.update();
      this.render();
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  stop() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
  }

  update() {
    if (!this.clock) return;
    const dt = Math.min(this.clock.getDelta(), 0.05);
    const elapsed = this.clock.getElapsedTime();

    // Smooth pointer look interpolation
    this.smoothLook.x += (this.targetLook.x - this.smoothLook.x) * 6 * dt;
    this.smoothLook.y += (this.targetLook.y - this.smoothLook.y) * 6 * dt;

    let targetPosX = 0;
    let targetPosZ = 0;
    let targetPosY = 0;
    let headYaw = this.smoothLook.x * 0.65;
    let headPitch = -this.smoothLook.y * 0.25;
    let headRoll = -this.smoothLook.x * 0.14;
    let holoIntensity = 0;

    if (this.isLookingUp) {
      headPitch += 0.42;
    }

    if (this.currentMood === 'idle') {
      headPitch += Math.sin(elapsed * 2.1) * 0.04;
      headRoll += Math.cos(elapsed * 1.5) * 0.035;
      this.bodySphere.rotation.z = Math.sin(elapsed * 1.4) * 0.03;
    } else if (this.currentMood === 'happy') {
      targetPosY = Math.abs(Math.sin(elapsed * 7.5)) * 0.24;
      headYaw += Math.sin(elapsed * 11) * 0.28;
      headRoll += Math.cos(elapsed * 9) * 0.16;
      this.bodySphere.rotation.y += dt * 2.4;
    } else if (this.currentMood === 'patrol') {
      const orbitRadius = 0.55;
      const angularSpeed = 1.35;
      this.patrolAngle += angularSpeed * dt;

      const nextX = Math.cos(this.patrolAngle) * orbitRadius;
      const nextZ = Math.sin(this.patrolAngle) * (orbitRadius * 0.5);

      const dx = nextX - this.bb8Root.position.x;
      const dz = nextZ - this.bb8Root.position.z;
      const stepDist = Math.hypot(dx, dz);

      this.bb8Root.position.x = nextX;
      this.bb8Root.position.z = nextZ;

      if (stepDist > 0.0001) {
        const THREE = window.THREE;
        const moveDir = new THREE.Vector3(dx, 0, dz).normalize();
        const rollAxis = new THREE.Vector3(moveDir.z, 0, -moveDir.x).normalize();
        this.bodySphere.rotateOnWorldAxis(rollAxis, stepDist / this.BODY_RADIUS);

        const heading = Math.atan2(dx, dz);
        headYaw = heading + Math.sin(elapsed * 4) * 0.18;
        headPitch += 0.14;
        headRoll = -0.14;
      }
    } else if (this.currentMood === 'curious') {
      headRoll = Math.sin(elapsed * 2.4) * 0.34;
      headPitch += -0.14 + Math.cos(elapsed * 3.0) * 0.08;
      headYaw += Math.sin(elapsed * 1.7) * 0.35;
    } else if (this.currentMood === 'hologram') {
      holoIntensity = 1.0;
      headPitch += -0.12;
      headYaw += Math.sin(elapsed * 1.2) * 0.15;
    }

    // Click reaction bounce
    if (this.excitedBounceTime > 0) {
      this.excitedBounceTime = Math.max(0, this.excitedBounceTime - dt);
      targetPosY += Math.abs(Math.sin(this.excitedBounceTime * 14)) * 0.22 * (this.excitedBounceTime / 1.4);
      headYaw += Math.sin(this.excitedBounceTime * 22) * 0.25;
    }

    if (this.currentMood !== 'patrol') {
      this.bb8Root.position.x += (targetPosX - this.bb8Root.position.x) * 5 * dt;
      this.bb8Root.position.z += (targetPosZ - this.bb8Root.position.z) * 5 * dt;
    }
    this.bb8Root.position.y += (targetPosY - this.bb8Root.position.y) * 12 * dt;

    this.headSpinGroup.rotation.y += (headYaw - this.headSpinGroup.rotation.y) * 8 * dt;
    this.headTiltGroup.rotation.x += (headPitch - this.headTiltGroup.rotation.x) * 8 * dt;
    this.headTiltGroup.rotation.z += (headRoll - this.headTiltGroup.rotation.z) * 8 * dt;

    if (this.holoBeamMesh && this.holoLensLight) {
      const targetOpacity = holoIntensity > 0 ? 0.22 + Math.sin(elapsed * 18) * 0.04 : 0;
      this.holoBeamMesh.material.opacity += (targetOpacity - this.holoBeamMesh.material.opacity) * 8 * dt;
      this.holoLensLight.intensity += (holoIntensity * 2.4 - this.holoLensLight.intensity) * 8 * dt;
    }

    if (this.dockPadGroup && this.dockPadGroup.visible) {
      this.dockPadGroup.rotation.y += dt * 0.35;
    }
  }

  render() {
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  _init2DFallback() {
    // Graceful fallback for non-WebGL environments
    if (this.canvas) {
      const ctx = this.canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = '#ff6b00';
        ctx.font = '12px sans-serif';
        ctx.fillText('BB-8 Buddy', 20, 20);
      }
    }
  }
}

window.BB8_3D = BB8_3D;

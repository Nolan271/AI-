# Video Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that takes user requirements, calls `ui-ux-pro-max` for visual polish, generates HyperFrames scenes with a 3D avatar PiP overlay, and renders `.mp4`.

**Architecture:** A `video-agent` skill orchestrates the pipeline. `templates/` provides scene blueprints. Three.js renders the 3D avatar as a PiP overlay synced via `hf-seek`. `ui-ux-pro-max` injects style tokens at design time.

**Tech Stack:** Claude Code Skill (YAML + MD), HyperFrames 0.6.20, Three.js, GSAP, TTS (say.js / hyperframes-media)

---

### Phase 0: Scaffolding

### Task 0.1: Create directory structure

**Files:**
- Create: `agent/skill.yaml`
- Create: `agent/workflows/generate-video.md`
- Create: `agent/prompts/analyze-requirement.md`
- Create: `agent/prompts/generate-script.md`
- Create: `agent/prompts/design-storyboard.md`
- Create: `agent/prompts/apply-style-tokens.md`
- Create: `agent/prompts/avatar-dialogue.md`
- Create: `templates/corporate/manifest.json`
- Create: `templates/corporate/scenes/01-welcome.html`
- Create: `templates/corporate/scenes/02-content.html`
- Create: `templates/corporate/scenes/03-avatar.html`
- Create: `templates/corporate/scenes/04-data.html`
- Create: `templates/corporate/scenes/05-closing.html`
- Create: `templates/corporate/style/tokens.css`
- Create: `compositions/components/avatar-overlay.js`
- Create: `assets/3d-avatar/` (directory)

- [ ] **Step 1: Create all directories**

Run:
```bash
mkdir -p "D:/Users/muzhi/Desktop/hhDome/my-video/agent/workflows"
mkdir -p "D:/Users/muzhi/Desktop/hhDome/my-video/agent/prompts"
mkdir -p "D:/Users/muzhi/Desktop/hhDome/my-video/templates/corporate/scenes"
mkdir -p "D:/Users/muzhi/Desktop/hhDome/my-video/templates/corporate/style"
mkdir -p "D:/Users/muzhi/Desktop/hhDome/my-video/assets/3d-avatar"
```

- [ ] **Step 2: Copy reference audio into project**

Run:
```bash
cp "D:/Users/muzhi/Desktop/hhDome/阳光甜美.mp3" "D:/Users/muzhi/Desktop/hhDome/my-video/assets/reference-audio/"
```

- [ ] **Step 3: Commit scaffolding**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add agent/ templates/ assets/reference-audio/ compositions/components/
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: scaffold video-agent directories and reference audio"
```

---

### Phase 1: Template System

### Task 1.1: Corporate template manifest

**Files:**
- Create: `templates/corporate/manifest.json`

- [ ] **Step 1: Write manifest.json**

```json
{
  "templateId": "corporate",
  "name": "企业宣传片",
  "description": "通用企业宣传/文化/制度介绍视频",
  "sceneCount": 5,
  "scenes": [
    { "id": "welcome",  "label": "开场欢迎",   "duration": 15, "hasAvatar": true },
    { "id": "content",  "label": "核心内容",    "duration": 30, "hasAvatar": false },
    { "id": "avatar",   "label": "虚拟人讲解",  "duration": 20, "hasAvatar": true },
    { "id": "data",     "label": "数据展示",    "duration": 20, "hasAvatar": false },
    { "id": "closing",  "label": "结尾",       "duration": 10, "hasAvatar": true }
  ],
  "defaultStyle": {
    "mood": "professional",
    "primaryColor": "#c9a84c",
    "bgColor": "#080c18",
    "textColor": "#efe8dc",
    "fontHeading": "Noto Serif SC",
    "fontBody": "Noto Sans SC"
  },
  "avatarStrategy": "opening+closing",
  "totalDuration": 95
}
```

- [ ] **Step 2: Commit**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add templates/corporate/manifest.json
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add corporate template manifest"
```

---

### Task 1.2: Corporate template scene - Welcome

**Files:**
- Create: `templates/corporate/scenes/01-welcome.html`

- [ ] **Step 1: Create welcome.html (占位符版, 可被 skill 注入内容)**

```html
<template id="scene-welcome-template">
  <div data-composition-id="scene-welcome" data-width="1920" data-height="1080">
    <div class="vignette"></div>
    <div class="glow-center"></div>
    <div class="ghost-text gold-gradient" style="font-size:280px;top:-20px;right:60px;">{{COMPANY_NAME}}</div>
    <div class="corner-tl"></div><div class="corner-tr"></div>
    <div class="corner-bl"></div><div class="corner-br"></div>
    <div class="bottom-bar"></div>

    <div class="scene-content center-text">
      <div class="accent-line center short" id="w-s1-line"></div>
      <div class="label-gold" id="w-s1-label">{{LABEL}}</div>
      <div class="headline-serif large" id="w-s1-title" style="font-size:78px;">
        {{TITLE_LINE1}}<br/>{{TITLE_LINE2}}
      </div>
      <div class="body-text light" id="w-s1-sub" style="margin-top:20px; max-width:900px;">
        {{SUBTITLE}}
      </div>
    </div>
    <div class="logo-text">{{COMPANY_NAME}}</div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      tl.from("#w-s1-line",  { scaleX: 0, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
      tl.from("#w-s1-label", { y: 30, opacity: 0, duration: 0.5, ease: "power2.out" }, 0.5);
      tl.from("#w-s1-title", { y: 40, opacity: 0, duration: 0.7, ease: "expo.out" }, 0.8);
      tl.from("#w-s1-sub",   { y: 25, opacity: 0, duration: 0.5, ease: "power2.out" }, 1.4);
      window.__timelines["scene-welcome"] = tl;
    </script>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add templates/corporate/scenes/01-welcome.html
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add welcome scene template with placeholders"
```

---

### Task 1.3: Corporate template scenes - Content, Avatar, Data, Closing

**Files:**
- Create: `templates/corporate/scenes/02-content.html`
- Create: `templates/corporate/scenes/03-avatar.html`
- Create: `templates/corporate/scenes/04-data.html`
- Create: `templates/corporate/scenes/05-closing.html`

- [ ] **Step 1: Create content.html (核心内容展示)**

```html
<template id="scene-content-template">
  <div data-composition-id="scene-content" data-width="1920" data-height="1080">
    <div class="vignette"></div>
    <div class="glow-bottom" style="left:50%;transform:translateX(-50%);"></div>
    <div class="ghost-text gold-gradient" style="font-size:140px;top:50%;right:60px;transform:translateY(-50%);">{{COMPANY_NAME}}</div>
    <div class="corner-tl"></div><div class="corner-tr"></div>
    <div class="corner-bl"></div><div class="corner-br"></div>
    <div class="bottom-bar"></div>

    <div class="scene-content">
      <div class="accent-line" id="c-s1-line"></div>
      <div class="label-gold" id="c-s1-label">{{SECTION_TITLE}}</div>
      <div class="headline-serif" id="c-s1-headline" style="font-size:54px; margin-top:8px;">
        {{HEADLINE}}
      </div>
      <div class="body-text" id="c-s1-body" style="margin-top:20px;">
        {{BODY_TEXT}}
      </div>
      {{EXTRA_CONTENT}}
    </div>
    <div class="logo-text">{{COMPANY_NAME}}</div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      tl.from("#c-s1-line",     { scaleX: 0, opacity: 0, duration: 0.5, ease: "power3.out" }, 0);
      tl.from("#c-s1-label",    { y: 25, opacity: 0, duration: 0.4, ease: "power2.out" }, 0.2);
      tl.from("#c-s1-headline", { y: 30, opacity: 0, duration: 0.6, ease: "expo.out" }, 0.8);
      tl.from("#c-s1-body",     { y: 20, opacity: 0, duration: 0.5, ease: "power2.out" }, 1.4);
      window.__timelines["scene-content"] = tl;
    </script>
  </div>
</template>
```

- [ ] **Step 2: Create avatar.html (虚拟人口播场景 - 含 PiP 插槽)**

```html
<template id="scene-avatar-template">
  <div data-composition-id="scene-avatar" data-width="1920" data-height="1080">
    <div class="vignette"></div>
    <div class="glow-center" style="opacity:0.6;"></div>

    <div class="scene-content" style="max-width:75%;">
      <div class="accent-line" id="a-s1-line"></div>
      <div class="headline-serif small" id="a-s1-title" style="font-size:42px;">
        {{AVATAR_LINE}}
      </div>
      <div class="body-text light" id="a-s1-body" style="margin-top:16px; max-width:1000px;">
        {{AVATAR_SPEECH}}
      </div>
    </div>

    <!-- PiP 虚拟人插槽: avatar-overlay.js 会挂载到此容器 -->
    <div id="avatar-pip-container"
         style="position:absolute; bottom:60px; right:60px; width:320px; height:480px;
                border-radius:16px; overflow:hidden; box-shadow:0 8px 40px rgba(0,0,0,0.5);
                border:1px solid rgba(201,168,76,0.3); z-index:10;">
      <div id="avatar-three-root" style="width:100%;height:100%;"></div>
    </div>

    <div class="bottom-bar"></div>
    <div class="logo-text">{{COMPANY_NAME}}</div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js"
      }
    }
    </script>
    <script type="module" src="{{AVATAR_SCRIPT_PATH}}"></script>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      tl.from("#a-s1-line",  { scaleX: 0, opacity: 0, duration: 0.5, ease: "power3.out" }, 0);
      tl.from("#a-s1-title", { y: 25, opacity: 0, duration: 0.5, ease: "power2.out" }, 0.3);
      tl.from("#a-s1-body",  { y: 20, opacity: 0, duration: 0.6, ease: "power2.out" }, 0.9);
      tl.from("#avatar-pip-container", { scale: 0.8, opacity: 0, duration: 0.5, ease: "back.out(1.7)" }, 1.5);
      window.__timelines["scene-avatar"] = tl;
    </script>
  </div>
</template>
```

- [ ] **Step 3: Create data.html (数据/信息展示)**

```html
<template id="scene-data-template">
  <div data-composition-id="scene-data" data-width="1920" data-height="1080">
    <div class="vignette"></div>
    <div class="ghost-text gold-gradient" style="font-size:200px;bottom:-30px;right:-20px;">{{DATA_GHOST}}</div>
    <div class="corner-tl"></div><div class="corner-tr"></div>
    <div class="corner-bl"></div><div class="corner-br"></div>
    <div class="bottom-bar"></div>

    <div class="scene-content center-text">
      <div class="accent-line center" id="d-s1-line"></div>
      <div class="label-gold" id="d-s1-label">{{DATA_LABEL}}</div>
      <div class="info-grid" id="d-s1-grid" style="justify-content:center; margin-top:20px;">
        {{DATA_CARDS}}
      </div>
    </div>
    <div class="logo-text">{{COMPANY_NAME}}</div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      tl.from("#d-s1-line",  { scaleX: 0, opacity: 0, duration: 0.5, ease: "power3.out" }, 0);
      tl.from("#d-s1-label", { y: 25, opacity: 0, duration: 0.4, ease: "power2.out" }, 0.3);
      tl.from(".info-card",  { y: 30, opacity: 0, scale: 0.95, duration: 0.5, ease: "power2.out", stagger: 0.12 }, 1.0);
      window.__timelines["scene-data"] = tl;
    </script>
  </div>
</template>
```

- [ ] **Step 4: Create closing.html (结尾)**

```html
<template id="scene-closing-template">
  <div data-composition-id="scene-closing" data-width="1920" data-height="1080">
    <div class="vignette"></div>
    <div class="glow-center" style="opacity:0.8;"></div>
    <div class="corner-tl"></div><div class="corner-tr"></div>
    <div class="corner-bl"></div><div class="corner-br"></div>

    <div class="scene-content center-text">
      <div class="accent-line center short" id="end-line"></div>
      <div class="headline-serif large" id="end-title" style="font-size:72px;">
        {{CLOSING_TITLE}}
      </div>
      <div class="closing-sub" id="end-sub">
        {{CLOSING_SUB}}
      </div>

      <!-- PiP 虚拟人插槽 (结尾告别) -->
      <div id="avatar-pip-container-closing"
           style="position:absolute; bottom:60px; right:60px; width:280px; height:420px;
                  border-radius:16px; overflow:hidden; box-shadow:0 8px 40px rgba(0,0,0,0.5);
                  border:1px solid rgba(201,168,76,0.3); z-index:10;">
        <div id="avatar-three-root-closing" style="width:100%;height:100%;"></div>
      </div>
    </div>
    <div class="bottom-bar"></div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      var tl = gsap.timeline({ paused: true });
      tl.from("#end-line", { scaleX: 0, opacity: 0, duration: 0.5, ease: "power3.out" }, 0);
      tl.from("#end-title",{ y: 30, opacity: 0, duration: 0.7, ease: "expo.out" }, 0.4);
      tl.from("#end-sub",  { y: 20, opacity: 0, duration: 0.5, ease: "power2.out" }, 1.2);
      tl.from("#avatar-pip-container-closing", { scale: 0.8, opacity: 0, duration: 0.5, ease: "back.out(1.7)" }, 1.8);
      window.__timelines["scene-closing"] = tl;
    </script>
  </div>
</template>
```

- [ ] **Step 5: Create tokens.css**

```css
/* Corporate template — design tokens */
/* Autogenerated, modified by ui-ux-pro-max at generation time */
:root {
  --color-primary: #c9a84c;
  --color-primary-rgb: 201, 168, 76;
  --color-bg: #080c18;
  --color-bg-card: rgba(21, 34, 56, 0.7);
  --color-text: #efe8dc;
  --color-text-body: #8a9bb0;
  --color-text-light: #b8c4d4;
  --color-border: rgba(201, 168, 76, 0.12);
  --color-accent-glow: rgba(212, 160, 56, 0.15);

  --font-heading: "Noto Serif SC", "STSong", serif;
  --font-body: "Noto Sans SC", "Microsoft YaHei", sans-serif;

  --ease-enter: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-exit: cubic-bezier(0.7, 0, 0.84, 0);
  --duration-fast: 0.4s;
  --duration-med: 0.6s;
  --duration-slow: 0.8s;
}
```

- [ ] **Step 6: Commit all template scenes**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add templates/corporate/scenes/ templates/corporate/style/
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add corporate template scenes (content, avatar, data, closing)"
```

---

### Phase 2: 3D Virtual Human (Three.js PiP)

### Task 2.1: Create Three.js avatar overlay component

**Files:**
- Create: `compositions/components/avatar-overlay.js`

This is the core 3D avatar module. It creates a stylized female 3D character using Three.js primitives, mounts into a container element, and responds to `hf-seek` events for HyperFrames sync.

- [ ] **Step 1: Write avatar-overlay.js**

```javascript
// 3D Avatar overlay for HyperFrames
// Stylized female character built with Three.js primitives
// Mounts into #avatar-pip-container or #avatar-pip-container-closing

(function () {
  'use strict';

  const AVATAR_CONFIG = {
    skinColor: 0xf5d6c6,
    hairColor: 0x4a3728,
    dressColor: 0xc9a84c,
    eyeColor: 0x553a2e,
    idleSwayAmplitude: 0.008,
    idleSwaySpeed: 0.5,
    blinkInterval: 3000,
  };

  class AvatarOverlay {
    constructor(containerId) {
      this.container = document.getElementById(containerId);
      if (!this.container) return;
      this.ready = false;
      this.mouthOpen = 0;
      this.isSpeaking = false;
      this.init();
    }

    init() {
      const w = this.container.clientWidth || 320;
      const h = this.container.clientHeight || 480;

      // Scene
      this.scene = new THREE.Scene();

      // Camera
      this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
      this.camera.position.set(0, 1.4, 3.2);
      this.camera.lookAt(0, 1.2, 0);

      // Renderer
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
      });
      this.renderer.setSize(w, h);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.setClearColor(0x000000, 0);
      this.container.appendChild(this.renderer.domElement);

      // Lights
      const ambient = new THREE.AmbientLight(0xffffff, 0.6);
      this.scene.add(ambient);
      const key = new THREE.DirectionalLight(0xffeedd, 1.2);
      key.position.set(2, 3, 4);
      this.scene.add(key);
      const fill = new THREE.DirectionalLight(0x8888ff, 0.4);
      fill.position.set(-2, 1, 2);
      this.scene.add(fill);
      const rim = new THREE.DirectionalLight(0xc9a84c, 0.3);
      rim.position.set(0, -1, -3);
      this.scene.add(rim);

      // Build character
      this.buildCharacter();

      // Start animation loop
      this.clock = new THREE.Clock();
      this.animate();

      // Listen for HyperFrames seek events
      window.addEventListener('hf-seek', (e) => {
        this.onSeek(e.detail);
      });

      this.ready = true;
    }

    buildCharacter() {
      const group = new THREE.Group();

      // Body (dress — rounded cylinder)
      const bodyGeo = new THREE.CylinderGeometry(0.45, 0.55, 0.9, 12);
      const bodyMat = new THREE.MeshStandardMaterial({
        color: AVATAR_CONFIG.dressColor,
        roughness: 0.6,
        metalness: 0.1,
      });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.position.y = 0.45;
      group.add(body);

      // Neck
      const neckGeo = new THREE.CylinderGeometry(0.15, 0.18, 0.1);
      const skinMat = new THREE.MeshStandardMaterial({
        color: AVATAR_CONFIG.skinColor,
        roughness: 0.4,
      });
      const neck = new THREE.Mesh(neckGeo, skinMat);
      neck.position.y = 0.95;
      group.add(neck);

      // Head
      const headGroup = new THREE.Group();
      headGroup.position.y = 1.25;

      const headGeo = new THREE.SphereGeometry(0.28, 16, 16);
      const head = new THREE.Mesh(headGeo, skinMat);
      headGroup.add(head);

      // Hair (bob style — half sphere on top)
      const hairMat = new THREE.MeshStandardMaterial({
        color: AVATAR_CONFIG.hairColor,
        roughness: 0.8,
      });
      const hairGeo = new THREE.SphereGeometry(0.3, 12, 12, 0, Math.PI * 2, 0, Math.PI * 0.5);
      const hair = new THREE.Mesh(hairGeo, hairMat);
      hair.position.y = 0.05;
      headGroup.add(hair);

      // Hair sides (two buns/clips)
      for (let side = -1; side <= 1; side += 2) {
        const sideHair = new THREE.Mesh(
          new THREE.SphereGeometry(0.08, 8, 8),
          hairMat
        );
        sideHair.position.set(side * 0.28, -0.04, 0);
        headGroup.add(sideHair);
      }

      // Eyes
      this.eyeLids = [];
      for (let side = -1; side <= 1; side += 2) {
        const eyeGroup = new THREE.Group();
        eyeGroup.position.set(side * 0.12, 0.04, 0.26);

        // Eyeball (white)
        const whiteMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
        const eyeball = new THREE.Mesh(
          new THREE.SphereGeometry(0.05, 8, 8),
          whiteMat
        );
        eyeGroup.add(eyeball);

        // Pupil
        const pupilMat = new THREE.MeshStandardMaterial({
          color: AVATAR_CONFIG.eyeColor,
        });
        const pupil = new THREE.Mesh(
          new THREE.SphereGeometry(0.025, 8, 8),
          pupilMat
        );
        pupil.position.z = 0.04;
        eyeGroup.add(pupil);

        // Eyelid (for blinking)
        const lidMat = new THREE.MeshStandardMaterial({
          color: AVATAR_CONFIG.skinColor,
        });
        const lid = new THREE.Mesh(
          new THREE.BoxGeometry(0.09, 0.005, 0.01),
          lidMat
        );
        lid.position.z = 0.05;
        lid.name = 'eyelid';
        eyeGroup.add(lid);
        this.eyeLids.push(lid);

        headGroup.add(eyeGroup);
      }

      // Mouth
      this.mouth = new THREE.Mesh(
        new THREE.SphereGeometry(0.025, 6, 6),
        new THREE.MeshStandardMaterial({ color: 0xcc6666 })
      );
      this.mouth.position.set(0, -0.04, 0.28);
      this.mouth.scale.y = 0.3;
      headGroup.add(this.mouth);

      // Blush (two small circles)
      for (let side = -1; side <= 1; side += 2) {
        const blush = new THREE.Mesh(
          new THREE.CircleGeometry(0.04, 8),
          new THREE.MeshStandardMaterial({
            color: 0xffaaaa,
            transparent: true,
            opacity: 0.25,
          })
        );
        blush.position.set(side * 0.15, -0.02, 0.26);
        headGroup.add(blush);
      }

      group.add(headGroup);
      this.headGroup = headGroup;
      this.characterGroup = group;
      this.scene.add(group);
    }

    animate() {
      if (!this.ready) return;
      requestAnimationFrame(() => this.animate());

      const t = this.clock.getElapsedTime();

      // Idle sway
      this.characterGroup.rotation.z =
        Math.sin(t * AVATAR_CONFIG.idleSwaySpeed) * AVATAR_CONFIG.idleSwayAmplitude;
      this.characterGroup.rotation.x =
        Math.sin(t * AVATAR_CONFIG.idleSwaySpeed * 0.7) * AVATAR_CONFIG.idleSwayAmplitude * 0.5;

      // Blink
      if (Math.sin(t * (1000 / AVATAR_CONFIG.blinkInterval)) > 0.95) {
        this.eyeLids.forEach((lid) => { lid.scale.y = 1; });
      } else {
        this.eyeLids.forEach((lid) => { lid.scale.y = 0.01; });
      }

      // Mouth (lip sync simulation)
      if (this.isSpeaking) {
        const breath = Math.sin(t * 6) * 0.5 + 0.5;
        this.mouth.scale.y = 0.2 + breath * 0.6;
        this.mouth.scale.x = 0.8 + breath * 0.2;
      } else {
        this.mouth.scale.y = 0.3;
        this.mouth.scale.x = 1.0;
      }

      this.renderer.render(this.scene, this.camera);
    }

    setSpeaking(speaking) {
      this.isSpeaking = speaking;
    }

    onSeek(detail) {
      // hf-seek fires at each frame during preview/render
      // detail = { time, compositionId, ... }
      // This allows precise sync — e.g., trigger gestures at specific times
    }
  }

  // Auto-mount on DOM ready
  function mountAvatars() {
    const containers = ['avatar-pip-container', 'avatar-pip-container-closing'];
    containers.forEach((id) => {
      if (document.getElementById(id)) {
        new AvatarOverlay(id);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountAvatars);
  } else {
    mountAvatars();
  }
})();
```

- [ ] **Step 2: Update package.json to add three dependency**

Edit `package.json` to add three.js:

```
  "devDependencies": {
    "hyperframes": "^0.6.20",
    "three": "^0.170.0"
  }
```

- [ ] **Step 3: Install three.js**

Run:
```bash
cd "D:/Users/muzhi/Desktop/hhDome/my-video" && npm install
```

- [ ] **Step 4: Commit avatar component**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add compositions/components/avatar-overlay.js package.json package-lock.json
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add Three.js 3D avatar PiP overlay component"
```

---

### Phase 3: Video-Agent Skill Definition

### Task 3.1: Create skill.yaml

**Files:**
- Create: `agent/skill.yaml`

- [ ] **Step 1: Write skill.yaml**

```yaml
name: video-agent
description: >
  Universal video generation agent. Takes user requirements, calls ui-ux-pro-max
  for visual polish, generates HyperFrames scenes with optional 3D avatar PiP,
  and renders .mp4. Supports corporate, educational, product, and custom video types.
prompt: |
  # Video Agent — 智能视频生成

  You are a video production agent. Your job is to turn user requirements into a
  polished .mp4 video using HyperFrames.

  ## Workflow

  1. **需求分析**: 读取 `agent/prompts/analyze-requirement.md`，根据用户输入提取结构化信息
  2. **用户确认 ①**: 展示需求卡片，让用户确认或修改
  3. **视觉风格设计**: 调用 `ui-ux-pro-max` 技能，输入视频类型+风格关键词，获取配色/字体/装饰方案
  4. **脚本生成**: 读取 `agent/prompts/generate-script.md`，生成分场景文案和虚拟人口播台词
  5. **用户确认 ②**: 展示完整脚本和分镜描述
  6. **模板匹配**: 根据视频类型从 `templates/` 选择对应模板
  7. **风格注入**: 调用 `ui-ux-pro-max` 优化动画曲线和视觉细节；读取 `agent/prompts/apply-style-tokens.md`
  8. **合成生成**: 注入内容到模板 → 生成 `compositions/[job-id]/` 下所有文件
  9. **渲染**: `npm run render`

  ## Key Files
  - `templates/` — 模板库，按类型分类
  - `compositions/components/avatar-overlay.js` — 3D 虚拟人组件
  - `agent/prompts/` — 各环节提示词
  - `assets/reference-audio/` — 参考音色文件

  ## Rules
  - 每个视觉环节都必须调用 `ui-ux-pro-max` 优化
  - 虚拟人出镜策略参考 `templates/[type]/manifest.json` 中的 avatarStrategy
  - 音频风格优先匹配 `assets/reference-audio/` 下的参考文件
```

- [ ] **Step 2: Commit skill.yaml**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add agent/skill.yaml
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add video-agent skill definition"
```

---

### Task 3.2: Create workflow document

**Files:**
- Create: `agent/workflows/generate-video.md`

- [ ] **Step 1: Write workflow document**

```markdown
# Video Generation Workflow

> 用户输入需求 → 多轮确认 + ui-ux-pro-max 美化 → 3D虚拟人口播 → 渲染出片

## Step-by-Step

### Step 1: 接收用户需求
用户输入自由文本描述想要的视频。

### Step 2: 结构化提取
读取 `agent/prompts/analyze-requirement.md` 并执行提取逻辑。
输出 JSON 格式的需求卡片。

### Step 3: 用户确认需求 (Checkpoint 1)
展示:
```json
{
  "videoType": "corporate",
  "topic": "...",
  "duration": "...",
  "style": "...",
  "avatarPresence": "opening+closing"
}
```
用户确认或修改。

### Step 4: 视觉风格设计
- 调用 `ui-ux-pro-max` 技能
- 输入: 视频类型 + 风格关键词
- 输出: 配色方案 / 字体搭配 / 装饰风格 / 动画节奏 / 虚拟人外观建议

### Step 5: 脚本生成
读取 `agent/prompts/generate-script.md`。
调用 `agent/prompts/avatar-dialogue.md` 决定虚拟人哪些场景出镜。

### Step 6: 用户确认脚本 (Checkpoint 2)
展示完整分场景文案，用户可逐段修改。

### Step 7: 模板匹配与组合
1. 根据 videoType 选择 `templates/{type}/`
2. 读取 manifest.json 获取场景配置
3. 注入文案到模板占位符 `{{PLACEHOLDER}}`
4. 注入 `tokens.css` + ui-ux-pro-max 优化后的样式
5. 处理虚拟人场景: 写入正确的 `{{AVATAR_SCRIPT_PATH}}`
6. 生成主时间线 `index.html`
7. 复制音频参考用于 TTS

### Step 8: 渲染
```bash
cd [project]
npm run render
```

## 用户跳过确认
- 如果用户说"直接出片"，跳过 Step 3 和 Step 6
- 如果用户说"只确认一次"，默认在 Step 6 确认
```

- [ ] **Step 2: Commit workflow**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add agent/workflows/generate-video.md
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add video generation workflow document"
```

---

### Phase 4: Prompt Files

### Task 4.1: Create analyze-requirement prompt

**Files:**
- Create: `agent/prompts/analyze-requirement.md`

- [ ] **Step 1: Write analyze-requirement.md**

```markdown
# 需求分析提示词

从用户自由文本中提取结构化字段。逐个反问澄清。

## 提取字段
- **videoType**: corporate | educational | product | custom
- **topic**: 视频主题（简短描述）
- **duration**: 目标时长（秒）
- **style**: 风格关键词（现代/大气/温馨/活泼/简约等）
- **targetAudience**: 目标受众
- **keyPoints**: 核心要点列表
- **avatarPresence**: full | opening+closing | none
- **voiceStyle**: 参考音频文件名或风格描述

## 输出格式
```json
{
  "videoType": "...",
  "topic": "...",
  "duration": 120,
  "style": "...",
  "targetAudience": "...",
  "keyPoints": [],
  "avatarPresence": "opening+closing",
  "voiceStyle": "参考 assets/reference-audio/ 下的文件"
}
```
```

- [ ] **Step 2: Commit**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add agent/prompts/analyze-requirement.md
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add requirement analysis prompt"
```

---

### Task 4.2: Create remaining prompts

**Files:**
- Create: `agent/prompts/generate-script.md`
- Create: `agent/prompts/design-storyboard.md`
- Create: `agent/prompts/apply-style-tokens.md`
- Create: `agent/prompts/avatar-dialogue.md`

- [ ] **Step 1: Create generate-script.md**

```markdown
# 脚本生成提示词

根据确认的需求卡片生成分场景脚本。

## 输入
- 需求卡片 JSON
- 模板 manifest.json（场景结构）
- ui-ux-pro-max 输出的风格方案

## 输出格式

### Scene 1: [场景名] (0-15s)
**画面**: [视觉描述]
**配音**: "[台词内容]"
**虚拟人**: [出镜/不出镜]
**动画**: [动画效果描述]

### Scene 2: [场景名] (15-35s)
...
```

- [ ] **Step 2: Create design-storyboard.md**

```markdown
# 分镜设计提示词

为每个场景生成详细的视觉描述，供模板填充使用。

## 每个场景输出
- 背景设计（纯色/渐变/图片/视频）
- 布局（左文右图/居中/上下分栏）
- 元素列表（标题、正文、数据卡片、图片等）
- 转场效果（淡入淡出/滑动/缩放）
- 虚拟人位置（无/右下角PiP/全屏）
```

- [ ] **Step 3: Create apply-style-tokens.md**

```markdown
# 风格应用提示词

将 ui-ux-pro-max 输出的视觉方案转为 CSS token 和 GSAP 参数。

## 转换规则
1. 配色 → CSS 变量（--color-*）
2. 字体 → CSS font-family
3. 装饰风格 → CSS 效果类（渐变、发光等）
4. 动画节奏 → GSAP ease + duration 参数
5. 虚拟人外观 → 3D 材质颜色参数
```

- [ ] **Step 4: Create avatar-dialogue.md**

```markdown
# 虚拟人口播设计提示词

根据脚本和视频类型，决定虚拟人出镜策略。

## 决策规则
- **企业宣传片**: 开场欢迎 + 结尾告别出镜
- **教学视频**: 全程出镜（画面右下角）
- **产品介绍**: 开场 + 关键卖点出镜
- **其他**: 根据内容重要性和严肃程度判断

## 输出
- 哪些场景需要虚拟人
- 每段虚拟人台词
- 虚拟人情绪/动作提示（微笑、手势、点头等）
```

- [ ] **Step 5: Commit all prompts**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add agent/prompts/
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "feat: add all video-agent prompt files"
```

---

### Phase 5: CLAUDE.md Update & Integration

### Task 5.1: Update CLAUDE.md to reference video-agent workflow

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add video-agent section to CLAUDE.md**

Add at the end of `CLAUDE.md`:

```markdown
## Video Agent — 智能视频生成

当用户要求"生成视频"、"做个宣传片"、"做个教学视频"等时，执行以下流程：

1. 调用 `video-agent` skill
2. 按照 `agent/workflows/generate-video.md` 逐步推进
3. 每个视觉环节调用 `ui-ux-pro-max` 优化
4. 参考 `agent/prompts/` 下的各环节提示词
```

- [ ] **Step 2: Commit**

```bash
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" add CLAUDE.md
git -C "D:/Users/muzhi/Desktop/hhDome/my-video" commit -m "docs: add video-agent workflow reference in CLAUDE.md"
```

---

### Phase 6: End-to-End Validation

### Task 6.1: Verify the pipeline

- [ ] **Step 1: Run hyperframes check on existing compositions**

```bash
cd "D:/Users/muzhi/Desktop/hhDome/my-video" && npm run check
```
Expected: No errors.

- [ ] **Step 2: Verify template JSON is valid**

```bash
cd "D:/Users/muzhi/Desktop/hhDome/my-video" && node -e "JSON.parse(require('fs').readFileSync('templates/corporate/manifest.json','utf8')); console.log('OK')"
```
Expected: OK

- [ ] **Step 3: Verify avatar script syntax**

```bash
cd "D:/Users/muzhi/Desktop/hhDome/my-video" && node -e "require('fs').readFileSync('compositions/components/avatar-overlay.js','utf8'); console.log('OK')"
```
Expected: OK

- [ ] **Step 4: List final project structure**

```bash
cd "D:/Users/muzhi/Desktop/hhDome/my-video" && find . -maxdepth 4 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/renders/work/*' | sort
```

- [ ] **Step 5: Commit final state if any fixes needed**

---

## Summary

| Phase | What | Files |
|-------|------|-------|
| 0 | Scaffolding | Directories, reference audio |
| 1 | Template System | manifest.json + 5 scene templates + tokens.css |
| 2 | 3D Avatar | avatar-overlay.js (Three.js PiP) |
| 3 | Skill Definition | skill.yaml + workflow doc |
| 4 | Prompt Files | 5 prompt files |
| 5 | Integration | CLAUDE.md update |
| 6 | Validation | lint + syntax checks |

/**
 * Retro 8-Bit Chiptune BB-8 Sound Synthesizer via Web Audio API.
 * Generates authentic vintage arcade square-wave chirps, bleeps, and fanfare.
 */

class BB8SoundSystem {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  _getCtx() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    return this.ctx;
  }

  setEnabled(val) {
    this.enabled = Boolean(val);
  }

  /**
   * Retro 8-Bit Chiptune Greeting Chirp (Fast Square Wave Arpeggio)
   */
  playChirp() {
    if (!this.enabled) return;
    const ctx = this._getCtx();
    if (!ctx) return;

    const notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]; // C5, E5, G5, C6, E6
    const now = ctx.currentTime;

    notes.forEach((freq, i) => {
      const t = now + i * 0.035;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.08, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(t);
      osc.stop(t + 0.045);
    });
  }

  /**
   * Retro Arcade Victory / Success Fanfare
   */
  playSuccess() {
    if (!this.enabled) return;
    const ctx = this._getCtx();
    if (!ctx) return;

    const notes = [440, 554.37, 659.25, 880, 1108.73, 1318.51];
    const now = ctx.currentTime;

    notes.forEach((freq, i) => {
      const t = now + i * 0.045;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.09, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + (i === notes.length - 1 ? 0.25 : 0.05));

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(t);
      osc.stop(t + (i === notes.length - 1 ? 0.26 : 0.055));
    });
  }

  /**
   * Retro 8-Bit Break Chime (Warm descending cadence)
   */
  playBreak() {
    if (!this.enabled) return;
    const ctx = this._getCtx();
    if (!ctx) return;

    const notes = [783.99, 659.25, 523.25, 392.00]; // G5, E5, C5, G4
    const now = ctx.currentTime;

    notes.forEach((freq, i) => {
      const t = now + i * 0.09;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.12, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(t);
      osc.stop(t + 0.13);
    });
  }

  /**
   * Retro 8-Bit Recording Cue Beep
   */
  playRecBeep(isStart = true) {
    if (!this.enabled) return;
    const ctx = this._getCtx();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'square';
    osc.frequency.setValueAtTime(isStart ? 880 : 440, now);
    if (isStart) {
      osc.frequency.setValueAtTime(1320, now + 0.05);
    }

    gain.gain.setValueAtTime(0.07, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.11);
  }

  /**
   * Retro Teletype Key Click
   */
  playKeyClick() {
    if (!this.enabled) return;
    const ctx = this._getCtx();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(1200 + Math.random() * 400, now);

    gain.gain.setValueAtTime(0.03, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.02);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.025);
  }
}

window.bb8Audio = new BB8SoundSystem();

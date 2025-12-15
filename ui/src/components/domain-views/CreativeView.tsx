'use client';

import { DomainView } from '../DomainTabs';
import { ComfyUIQueuePanel, QuickGenerateButton } from '../embedded';

export function CreativeView() {
  return (
    <DomainView
      title="Creative"
      icon="🎨"
      description="Image generation, TTS, and creative tools"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.203:8188"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              color: 'var(--hydra-purple)',
              border: '1px solid var(--hydra-purple)',
            }}
          >
            ComfyUI →
          </a>
          <a
            href="http://192.168.1.244:8000"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(236, 72, 153, 0.1)',
              color: 'var(--hydra-magenta)',
              border: '1px solid var(--hydra-magenta)',
            }}
          >
            SillyTavern →
          </a>
          <a
            href="http://192.168.1.244:8880"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              color: 'var(--hydra-green)',
              border: '1px solid var(--hydra-green)',
            }}
          >
            Kokoro TTS →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Quick Generate Buttons */}
        <div>
          <div className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Quick Generate
          </div>
          <div className="flex flex-wrap gap-2">
            <QuickGenerateButton preset="portrait" prompt="Professional portrait" />
            <QuickGenerateButton preset="landscape" prompt="Fantasy landscape" />
            <QuickGenerateButton preset="concept" prompt="Concept art" />
            <QuickGenerateButton preset="anime" prompt="Anime style" />
            <QuickGenerateButton preset="photo" prompt="Photorealistic" />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* ComfyUI Queue */}
          <div className="col-span-2">
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <ComfyUIQueuePanel height={500} showHeader={true} />
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-4">
            {/* GPU Status for Creative */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Creative GPU
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span style={{ color: 'var(--hydra-text)' }}>RTX 5070 Ti #1</span>
                    <span style={{ color: 'var(--hydra-cyan)' }}>16 GB</span>
                  </div>
                  <div
                    className="h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: 'var(--hydra-border)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{ width: '45%', backgroundColor: 'var(--hydra-purple)' }}
                    />
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                    7.2 GB used • SDXL loaded
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span style={{ color: 'var(--hydra-text)' }}>RTX 5070 Ti #2</span>
                    <span style={{ color: 'var(--hydra-cyan)' }}>16 GB</span>
                  </div>
                  <div
                    className="h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: 'var(--hydra-border)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{ width: '30%', backgroundColor: 'var(--hydra-green)' }}
                    />
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                    4.8 GB used • Available
                  </div>
                </div>
              </div>
            </div>

            {/* TTS Panel */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                  Text-to-Speech
                </span>
                <span
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', color: 'var(--hydra-green)' }}
                >
                  Ready
                </span>
              </div>
              <div className="space-y-2">
                {[
                  { name: 'af_sarah', style: 'American Female', status: 'loaded' },
                  { name: 'bf_emma', style: 'British Female', status: 'available' },
                  { name: 'am_adam', style: 'American Male', status: 'available' },
                ].map((voice) => (
                  <div
                    key={voice.name}
                    className="flex items-center justify-between p-2 rounded text-sm"
                    style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                  >
                    <div>
                      <div style={{ color: 'var(--hydra-text)' }}>{voice.name}</div>
                      <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                        {voice.style}
                      </div>
                    </div>
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor:
                          voice.status === 'loaded' ? 'var(--hydra-green)' : 'var(--hydra-text-muted)',
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Character Templates */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                  Character Templates
                </span>
                <a
                  href="http://192.168.1.244:8000"
                  className="text-xs"
                  style={{ color: 'var(--hydra-cyan)' }}
                >
                  Manage →
                </a>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {['Luna', 'Atlas', 'Nova', 'Sage', 'Echo', 'Aria'].map((char) => (
                  <div
                    key={char}
                    className="p-2 rounded text-center text-sm cursor-pointer transition-all hover:scale-105"
                    style={{
                      backgroundColor: 'rgba(139, 92, 246, 0.1)',
                      border: '1px solid var(--hydra-border)',
                      color: 'var(--hydra-text)',
                    }}
                  >
                    {char}
                  </div>
                ))}
              </div>
            </div>

            {/* Empire of Broken Queens */}
            <div
              className="rounded-lg border p-4"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-magenta)',
                borderWidth: '2px',
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">👑</span>
                <span className="text-sm font-medium" style={{ color: 'var(--hydra-magenta)' }}>
                  Empire of Broken Queens
                </span>
              </div>
              <div className="text-xs mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
                Visual novel production pipeline
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Chapters</span>
                  <span style={{ color: 'var(--hydra-text)' }}>12 / 24</span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Portraits</span>
                  <span style={{ color: 'var(--hydra-text)' }}>48 generated</span>
                </div>
                <div className="flex justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Voice Lines</span>
                  <span style={{ color: 'var(--hydra-text)' }}>156 clips</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Model Info */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { name: 'SDXL Base', size: '6.94 GB', status: 'loaded', type: 'Checkpoint' },
            { name: 'VAE-FT', size: '335 MB', status: 'loaded', type: 'VAE' },
            { name: 'ControlNet Canny', size: '2.5 GB', status: 'loaded', type: 'ControlNet' },
            { name: 'IP-Adapter', size: '1.2 GB', status: 'available', type: 'Adapter' },
          ].map((model) => (
            <div
              key={model.name}
              className="p-3 rounded-lg border"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: model.status === 'loaded' ? 'var(--hydra-green)' : 'var(--hydra-border)',
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                  {model.name}
                </span>
                <span
                  className="w-2 h-2 rounded-full"
                  style={{
                    backgroundColor:
                      model.status === 'loaded' ? 'var(--hydra-green)' : 'var(--hydra-text-muted)',
                  }}
                />
              </div>
              <div className="flex justify-between text-xs">
                <span style={{ color: 'var(--hydra-text-muted)' }}>{model.type}</span>
                <span style={{ color: 'var(--hydra-cyan)' }}>{model.size}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DomainView>
  );
}

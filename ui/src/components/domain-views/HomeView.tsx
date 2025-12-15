'use client';

import { DomainView } from '../DomainTabs';
import { HomeControlWidget, SceneButton } from '../embedded';
import { VoiceInterfacePanel } from '../VoiceInterfacePanel';

export function HomeView() {
  return (
    <DomainView
      title="Home"
      icon="🏠"
      description="Smart home control, devices, and automation"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.244:8123"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              color: 'var(--hydra-cyan)',
              border: '1px solid var(--hydra-cyan)',
            }}
          >
            Home Assistant →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Quick Scenes */}
        <div>
          <div className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Quick Scenes
          </div>
          <div className="flex flex-wrap gap-2">
            <SceneButton scene="movieNight" />
            <SceneButton scene="workFocus" />
            <SceneButton scene="partyMode" />
            <SceneButton scene="goodnight" />
            <SceneButton scene="allOff" />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Home Control Widget */}
          <div className="col-span-2">
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <HomeControlWidget height={450} showHeader={true} />
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-4">
            {/* Current Status */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Home Status
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Mode</span>
                  <span
                    className="px-2 py-0.5 rounded text-xs"
                    style={{ backgroundColor: 'rgba(34, 197, 94, 0.2)', color: 'var(--hydra-green)' }}
                  >
                    Home
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Occupancy</span>
                  <span style={{ color: 'var(--hydra-text)' }}>1 person</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Security</span>
                  <span style={{ color: 'var(--hydra-green)' }}>Armed (Home)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Energy Today</span>
                  <span style={{ color: 'var(--hydra-yellow)' }}>42.3 kWh</span>
                </div>
              </div>
            </div>

            {/* Voice Interface */}
            <VoiceInterfacePanel />

            {/* GPU Power Management */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Cluster Power Mode
              </div>
              <div className="space-y-2">
                {[
                  { mode: 'Performance', power: '1200W', desc: 'Full power for inference', active: true },
                  { mode: 'Balanced', power: '800W', desc: 'Normal operation', active: false },
                  { mode: 'Eco', power: '400W', desc: 'Away mode savings', active: false },
                ].map((mode) => (
                  <button
                    key={mode.mode}
                    className="w-full p-2 rounded text-left transition-all"
                    style={{
                      backgroundColor: mode.active ? 'rgba(6, 182, 212, 0.2)' : 'rgba(0,0,0,0.2)',
                      border: mode.active ? '1px solid var(--hydra-cyan)' : '1px solid transparent',
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className="text-sm font-medium"
                        style={{ color: mode.active ? 'var(--hydra-cyan)' : 'var(--hydra-text)' }}
                      >
                        {mode.mode}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--hydra-yellow)' }}>
                        ~{mode.power}
                      </span>
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: 'var(--hydra-text-muted)' }}>
                      {mode.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Media Control */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                  Media
                </span>
                <a
                  href="http://192.168.1.244:32400"
                  className="text-xs"
                  style={{ color: 'var(--hydra-cyan)' }}
                >
                  Plex →
                </a>
              </div>
              <div className="space-y-2">
                {[
                  { zone: 'Living Room', status: 'Playing', media: 'Music' },
                  { zone: 'Office', status: 'Idle', media: '-' },
                  { zone: 'Bedroom', status: 'Off', media: '-' },
                ].map((zone) => (
                  <div
                    key={zone.zone}
                    className="flex items-center justify-between p-2 rounded text-sm"
                    style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                  >
                    <span style={{ color: 'var(--hydra-text)' }}>{zone.zone}</span>
                    <span
                      style={{
                        color:
                          zone.status === 'Playing'
                            ? 'var(--hydra-green)'
                            : zone.status === 'Idle'
                            ? 'var(--hydra-yellow)'
                            : 'var(--hydra-text-muted)',
                      }}
                    >
                      {zone.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Device Grid */}
        <div>
          <div className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Connected Devices
          </div>
          <div className="grid grid-cols-6 gap-3">
            {[
              { name: 'Lutron Hub', icon: '💡', status: 'online', count: 12 },
              { name: 'Nest Thermostat', icon: '🌡️', status: 'online', count: 1 },
              { name: 'Ring Doorbell', icon: '🔔', status: 'online', count: 2 },
              { name: 'Bond Bridge', icon: '🌀', status: 'online', count: 4 },
              { name: 'Sonos', icon: '🔊', status: 'online', count: 5 },
              { name: 'Smart Plugs', icon: '🔌', status: 'online', count: 8 },
            ].map((device) => (
              <div
                key={device.name}
                className="p-3 rounded-lg border text-center"
                style={{
                  backgroundColor: 'var(--hydra-bg)',
                  borderColor: device.status === 'online' ? 'var(--hydra-green)' : 'var(--hydra-border)',
                }}
              >
                <div className="text-2xl mb-1">{device.icon}</div>
                <div className="text-xs font-medium" style={{ color: 'var(--hydra-text)' }}>
                  {device.name}
                </div>
                <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  {device.count} devices
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Automations */}
        <div className="grid grid-cols-2 gap-6">
          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
              Active Automations
            </div>
            <div className="space-y-2">
              {[
                { name: 'Morning Routine', trigger: '6:00 AM', enabled: true },
                { name: 'Away Mode', trigger: 'Geofence', enabled: true },
                { name: 'GPU Eco Mode', trigger: 'Away + 15min', enabled: true },
                { name: 'Night Lights', trigger: 'Sunset', enabled: true },
                { name: 'Motion Lighting', trigger: 'Motion sensors', enabled: false },
              ].map((auto) => (
                <div
                  key={auto.name}
                  className="flex items-center justify-between p-2 rounded"
                  style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                >
                  <div>
                    <div className="text-sm" style={{ color: 'var(--hydra-text)' }}>
                      {auto.name}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      {auto.trigger}
                    </div>
                  </div>
                  <div
                    className="w-8 h-4 rounded-full relative cursor-pointer transition-colors"
                    style={{
                      backgroundColor: auto.enabled ? 'var(--hydra-green)' : 'var(--hydra-border)',
                    }}
                  >
                    <div
                      className="absolute w-3 h-3 rounded-full bg-white top-0.5 transition-all"
                      style={{ left: auto.enabled ? '1rem' : '0.125rem' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
              Recent Activity
            </div>
            <div className="space-y-2 text-sm">
              {[
                { time: '2 min ago', event: 'Office lights turned on', icon: '💡' },
                { time: '15 min ago', event: 'Thermostat set to 70°F', icon: '🌡️' },
                { time: '1 hour ago', event: 'Front door unlocked', icon: '🔓' },
                { time: '2 hours ago', event: 'Eco mode activated', icon: '🌱' },
                { time: '3 hours ago', event: 'Motion detected: Garage', icon: '🚶' },
              ].map((event, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 rounded"
                  style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                >
                  <span>{event.icon}</span>
                  <div className="flex-1">
                    <div style={{ color: 'var(--hydra-text)' }}>{event.event}</div>
                  </div>
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    {event.time}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DomainView>
  );
}

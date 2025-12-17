import React, { useState } from 'react';
import { Card, Button, Tabs, Badge, Modal, StatusDot, ProgressBar } from '../components/UIComponents';
import { MOCK_QUEENS, MOCK_SCENES, MOCK_DIALOGUES, MOCK_SPRITES, MOCK_RELATIONSHIPS, Scene, DialogueNode, SpriteAsset, Relationship } from '../constants';
import { Palette, MessageSquare, Heart, Image as ImageIcon, Sparkles, Play, Plus, MapPin, Users, FileText, GitBranch, Check, Clock, Edit2, Loader2, AlertCircle, ArrowRight, Smile, Frown, Angry, Zap } from 'lucide-react';
import { generateAsset } from '../services/geminiService';
import { Queen } from '../types';
import { useNotifications } from '../context/NotificationContext';

export const Studio: React.FC = () => {
  const [activeTab, setActiveTab] = useState('CHARACTERS');
  const [queens, setQueens] = useState<Queen[]>(MOCK_QUEENS);
  
  // Gen Modal State
  const [isGenModalOpen, setIsGenModalOpen] = useState(false);
  const [genPrompt, setGenPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  const { addNotification } = useNotifications();
  
  const tabs = [
    { id: 'CHARACTERS', label: 'Characters' },
    { id: 'SCENES', label: 'Scenes' },
    { id: 'DIALOGUE', label: 'Dialogue' },
    { id: 'SPRITES', label: 'Sprites' },
    { id: 'RELATIONSHIPS', label: 'Relationships' }
  ];

  const handleGenerate = async () => {
    if (!genPrompt.trim()) return;
    
    setIsGenerating(true);
    addNotification('info', 'Generation Started', 'Sending prompt to Gemini Engine...');
    
    try {
      const imageData = await generateAsset(genPrompt, 'character');
      
      if (imageData) {
        const newQueen: Queen = {
          id: Date.now().toString(),
          name: 'Generated Asset',
          title: 'The Unnamed',
          kingdom: 'Unknown',
          archetype: 'Neural Ghost',
          status: { dialogue: false, sprites: false, relationships: false },
          image: imageData
        };
        
        setQueens(prev => [newQueen, ...prev]);
        addNotification('success', 'Asset Generated', 'New character asset added to roster.');
        setGenPrompt('');
        setIsGenModalOpen(false);
      } else {
         addNotification('error', 'Generation Failed', 'Could not generate image. Check API limits.');
      }
    } catch (e) {
       addNotification('error', 'Generation Error', 'An error occurred during synthesis.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Gen Modal */}
      <Modal isOpen={isGenModalOpen} onClose={() => setIsGenModalOpen(false)} title="NEURAL ASSET SYNTHESIS">
        <div className="space-y-4">
           <div>
              <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Creative Prompt</label>
              <textarea 
                 value={genPrompt}
                 onChange={(e) => setGenPrompt(e.target.value)}
                 className="w-full bg-surface-dim border border-neutral-700 rounded-lg p-3 text-neutral-200 outline-none focus:border-purple-500 h-32 resize-none"
                 placeholder="Describe the character... (e.g. 'A cyborg queen with neon blue hair and chrome armor')"
              />
           </div>
           <div className="flex justify-end gap-3 pt-2">
              <Button variant="ghost" onClick={() => setIsGenModalOpen(false)}>Cancel</Button>
              <Button 
                variant="primary" 
                className="bg-purple-600 hover:bg-purple-500" 
                icon={isGenerating ? <Sparkles size={16} className="animate-spin" /> : <Sparkles size={16} />}
                onClick={handleGenerate}
                disabled={isGenerating || !genPrompt.trim()}
              >
                {isGenerating ? 'Synthesizing...' : 'Generate Asset'}
              </Button>
           </div>
        </div>
      </Modal>

      {/* Studio Header */}
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-purple-500">STUDIO</span> // EMPIRE OF BROKEN QUEENS
          </h2>
          <Tabs 
            tabs={tabs} 
            activeTab={activeTab} 
            onChange={setActiveTab} 
            className="mt-4"
            variant="purple"
          />
        </div>
        <div className="pb-2">
          <Button 
            variant="primary" 
            className="bg-purple-600 hover:bg-purple-500" 
            icon={<Sparkles size={16} />}
            onClick={() => setIsGenModalOpen(true)}
          >
             Generate Assets
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        
        {activeTab === 'CHARACTERS' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Character Roster</h3>
              <span className="text-xs font-mono text-neutral-500">{queens.length} / 100 ASSETS</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {queens.map((queen) => (
                <Card key={queen.id} className="group hover:border-purple-500/50 transition-colors">
                  <div className="aspect-square bg-neutral-900 rounded-lg mb-3 overflow-hidden relative">
                    <img 
                      src={queen.image} 
                      alt={queen.name}
                      className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                    />
                    <div className="absolute top-2 right-2 flex flex-col gap-1">
                      {queen.status.dialogue && <div className="p-1 bg-neutral-900/80 rounded text-emerald-400" title="Dialogue Ready"><MessageSquare size={12} /></div>}
                      {queen.status.sprites && <div className="p-1 bg-neutral-900/80 rounded text-cyan-400" title="Sprites Ready"><ImageIcon size={12} /></div>}
                      {queen.status.relationships && <div className="p-1 bg-neutral-900/80 rounded text-pink-400" title="Relationships Mapped"><Heart size={12} /></div>}
                    </div>
                  </div>
                  
                  <div className="space-y-1">
                    <h4 className="font-bold text-neutral-200">{queen.name}</h4>
                    <p className="text-xs text-purple-400 font-mono">{queen.title}</p>
                    <p className="text-xs text-neutral-500">{queen.kingdom}</p>
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-neutral-800">
                    <Badge variant="purple">{queen.archetype}</Badge>
                  </div>
                </Card>
              ))}
              
              {/* Add New Placeholder */}
              <button 
                onClick={() => setIsGenModalOpen(true)}
                className="border border-dashed border-neutral-700 rounded-xl flex flex-col items-center justify-center gap-2 text-neutral-600 hover:text-purple-400 hover:border-purple-500/50 transition-colors aspect-[3/4] xl:aspect-auto h-full min-h-[300px]"
              >
                <Plus size={24} />
                <span className="text-sm font-mono">GENERATE NEW</span>
              </button>
            </div>
          </div>
        )}

        {/* Scenes Tab */}
        {activeTab === 'SCENES' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Scene Library</h3>
              <div className="flex gap-2">
                <span className="text-xs font-mono text-neutral-500">
                  {MOCK_SCENES.filter(s => s.status === 'final').length} / {MOCK_SCENES.length} FINALIZED
                </span>
              </div>
            </div>

            {/* Scenes by Act */}
            {[1, 2, 3].map(act => {
              const actScenes = MOCK_SCENES.filter(s => s.act === act);
              if (actScenes.length === 0) return null;

              return (
                <div key={act} className="space-y-3">
                  <h4 className="text-sm font-mono text-purple-400 uppercase">Act {act}</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {actScenes.map(scene => (
                      <Card key={scene.id} className="hover:border-purple-500/30 transition-colors cursor-pointer">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-semibold text-neutral-200">{scene.name}</h4>
                            <p className="text-xs text-neutral-500">{scene.chapter}</p>
                          </div>
                          <Badge variant={
                            scene.status === 'final' ? 'emerald' :
                            scene.status === 'reviewed' ? 'cyan' :
                            scene.status === 'written' ? 'amber' : 'neutral'
                          }>
                            {scene.status}
                          </Badge>
                        </div>

                        <p className="text-sm text-neutral-400 mb-3 line-clamp-2">{scene.description}</p>

                        <div className="flex items-center gap-4 text-xs text-neutral-500">
                          <span className="flex items-center gap-1">
                            <MapPin size={12} /> {scene.location}
                          </span>
                          <span className="flex items-center gap-1">
                            <Users size={12} /> {scene.characters.length} characters
                          </span>
                        </div>

                        <div className="mt-3 pt-3 border-t border-neutral-800 flex flex-wrap gap-1">
                          {scene.characters.slice(0, 3).map(char => (
                            <span key={char} className="text-xs px-2 py-0.5 bg-neutral-800 rounded text-neutral-400">{char}</span>
                          ))}
                          {scene.characters.length > 3 && (
                            <span className="text-xs text-neutral-600">+{scene.characters.length - 3} more</span>
                          )}
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Dialogue Tab */}
        {activeTab === 'DIALOGUE' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Dialogue Trees</h3>
              <span className="text-xs font-mono text-neutral-500">{MOCK_DIALOGUES.length} NODES</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Dialogue by Scene */}
              {MOCK_SCENES.slice(0, 4).map(scene => {
                const sceneDialogues = MOCK_DIALOGUES.filter(d => d.sceneId === scene.id);
                if (sceneDialogues.length === 0) return null;

                return (
                  <Card key={scene.id} className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-neutral-200">{scene.name}</h4>
                      <span className="text-xs text-neutral-500">{sceneDialogues.length} lines</span>
                    </div>

                    <div className="space-y-3">
                      {sceneDialogues.map(dialogue => (
                        <div key={dialogue.id} className="relative">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center shrink-0">
                              {dialogue.emotion === 'happy' && <Smile size={14} className="text-emerald-400" />}
                              {dialogue.emotion === 'angry' && <Angry size={14} className="text-red-400" />}
                              {dialogue.emotion === 'sad' && <Frown size={14} className="text-blue-400" />}
                              {dialogue.emotion === 'seductive' && <Zap size={14} className="text-pink-400" />}
                              {(dialogue.emotion === 'neutral' || dialogue.emotion === 'surprised') && <MessageSquare size={14} className="text-neutral-400" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-sm font-medium text-purple-400">{dialogue.character}</span>
                                <span className="text-xs text-neutral-600">{dialogue.emotion}</span>
                              </div>
                              <p className="text-sm text-neutral-300 italic">"{dialogue.line}"</p>

                              {dialogue.choices && (
                                <div className="mt-2 space-y-1">
                                  {dialogue.choices.map((choice, idx) => (
                                    <div key={idx} className="flex items-center gap-2 text-xs text-cyan-400">
                                      <ArrowRight size={10} />
                                      <span>{choice.text}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Sprites Tab */}
        {activeTab === 'SPRITES' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Sprite Assets</h3>
              <div className="flex gap-4">
                <span className="text-xs font-mono text-emerald-400">
                  {MOCK_SPRITES.filter(s => s.status === 'approved').length} Approved
                </span>
                <span className="text-xs font-mono text-amber-400">
                  {MOCK_SPRITES.filter(s => s.status === 'generating').length} Generating
                </span>
                <span className="text-xs font-mono text-neutral-500">
                  {MOCK_SPRITES.filter(s => s.status === 'pending').length} Pending
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
              {MOCK_SPRITES.map(sprite => (
                <Card key={sprite.id} className="group hover:border-purple-500/30 transition-colors">
                  <div className="aspect-square bg-neutral-900 rounded-lg mb-3 overflow-hidden relative flex items-center justify-center">
                    {sprite.thumbnail ? (
                      <img
                        src={sprite.thumbnail}
                        alt={`${sprite.character} ${sprite.pose}`}
                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                      />
                    ) : (
                      <div className="text-neutral-700">
                        {sprite.status === 'generating' ? (
                          <Loader2 size={32} className="animate-spin" />
                        ) : (
                          <ImageIcon size={32} />
                        )}
                      </div>
                    )}

                    <div className="absolute top-2 right-2">
                      {sprite.status === 'approved' && (
                        <div className="p-1 bg-emerald-500/80 rounded"><Check size={10} className="text-white" /></div>
                      )}
                      {sprite.status === 'generating' && (
                        <div className="p-1 bg-amber-500/80 rounded"><Loader2 size={10} className="text-white animate-spin" /></div>
                      )}
                      {sprite.status === 'pending' && (
                        <div className="p-1 bg-neutral-600/80 rounded"><Clock size={10} className="text-white" /></div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <h4 className="text-sm font-semibold text-neutral-200">{sprite.character}</h4>
                    <p className="text-xs text-neutral-500 capitalize">{sprite.pose} / {sprite.expression}</p>
                    <p className="text-xs text-purple-400 font-mono">{sprite.outfit}</p>
                  </div>
                </Card>
              ))}

              {/* Add New Placeholder */}
              <button
                onClick={() => setIsGenModalOpen(true)}
                className="border border-dashed border-neutral-700 rounded-xl flex flex-col items-center justify-center gap-2 text-neutral-600 hover:text-purple-400 hover:border-purple-500/50 transition-colors aspect-square"
              >
                <Plus size={24} />
                <span className="text-xs font-mono">GENERATE</span>
              </button>
            </div>
          </div>
        )}

        {/* Relationships Tab */}
        {activeTab === 'RELATIONSHIPS' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Character Relationships</h3>
              <span className="text-xs font-mono text-neutral-500">{MOCK_RELATIONSHIPS.length} CONNECTIONS</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {MOCK_RELATIONSHIPS.map(rel => (
                <Card key={rel.id} className="hover:border-purple-500/30 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-neutral-200">{rel.from}</span>
                      <ArrowRight size={16} className="text-neutral-600" />
                      <span className="font-semibold text-neutral-200">{rel.to}</span>
                    </div>
                    <Badge variant={
                      rel.type === 'ally' ? 'emerald' :
                      rel.type === 'lover' ? 'purple' :
                      rel.type === 'rival' ? 'amber' :
                      rel.type === 'enemy' ? 'red' :
                      rel.type === 'complicated' ? 'cyan' : 'neutral'
                    }>
                      {rel.type}
                    </Badge>
                  </div>

                  <p className="text-sm text-neutral-400 mb-3">{rel.description}</p>

                  {/* Relationship Strength Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-mono text-neutral-500">
                      <span>AFFINITY</span>
                      <span>{rel.strength > 0 ? '+' : ''}{rel.strength}</span>
                    </div>
                    <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          rel.strength >= 50 ? 'bg-emerald-500' :
                          rel.strength > 0 ? 'bg-cyan-500' :
                          rel.strength === 0 ? 'bg-neutral-600' :
                          rel.strength > -50 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{
                          width: `${Math.abs(rel.strength)}%`,
                          marginLeft: rel.strength < 0 ? `${100 - Math.abs(rel.strength)}%` : '0'
                        }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-neutral-600">
                      <span>HOSTILE</span>
                      <span>NEUTRAL</span>
                      <span>DEVOTED</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Relationship Legend */}
            <div className="flex justify-center gap-4 pt-4 border-t border-neutral-800">
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Ally
              </span>
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <span className="w-2 h-2 rounded-full bg-purple-500" /> Lover
              </span>
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <span className="w-2 h-2 rounded-full bg-amber-500" /> Rival
              </span>
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Enemy
              </span>
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <span className="w-2 h-2 rounded-full bg-cyan-500" /> Complicated
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

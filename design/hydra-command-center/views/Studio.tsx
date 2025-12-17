import React, { useState } from 'react';
import { Card, Button, Tabs, Badge, Modal } from '../components/UIComponents';
import { MOCK_QUEENS } from '../constants';
import { Palette, MessageSquare, Heart, Image as ImageIcon, Sparkles, Play, Plus } from 'lucide-react';
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

        {/* Placeholder for other tabs */}
        {activeTab !== 'CHARACTERS' && (
          <div className="h-64 flex flex-col items-center justify-center text-neutral-600 border border-dashed border-neutral-800 rounded-xl">
             <Palette size={48} className="mb-4 text-neutral-800" />
             <p>Module {activeTab} initialized but waiting for input.</p>
          </div>
        )}
      </div>
    </div>
  );
};

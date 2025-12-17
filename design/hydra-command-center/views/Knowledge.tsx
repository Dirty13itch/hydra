import React, { useState } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import { MOCK_COLLECTIONS } from '../constants';
import { Database, Search, Upload, Book, FileText, RefreshCw } from 'lucide-react';

export const Knowledge: React.FC = () => {
  const [activeTab, setActiveTab] = useState('COLLECTIONS');
  const tabs = [
    { id: 'COLLECTIONS', label: 'Collections' },
    { id: 'SOURCES', label: 'Sources' },
    { id: 'SEARCH', label: 'Semantic Search' }
  ];

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Knowledge Header */}
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-cyan-500">KNOWLEDGE</span> // RAG PIPELINE
          </h2>
          <Tabs 
            tabs={tabs} 
            activeTab={activeTab} 
            onChange={setActiveTab} 
            className="mt-4"
            variant="emerald"
          />
        </div>
        <div className="pb-2 flex gap-2">
           <Button variant="secondary" size="sm" icon={<RefreshCw size={14} />}>Re-Index</Button>
           <Button variant="primary" size="sm" className="bg-cyan-600 hover:bg-cyan-500" icon={<Upload size={14} />}>Ingest</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        
        {activeTab === 'COLLECTIONS' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
               {/* Collection Stats */}
               <Card className="bg-surface-dim border-neutral-800">
                  <div className="flex items-center gap-3">
                     <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-500"><Book size={20} /></div>
                     <div>
                        <p className="text-xs text-neutral-500 font-mono">TOTAL DOCS</p>
                        <p className="text-xl font-mono font-bold text-neutral-200">169</p>
                     </div>
                  </div>
               </Card>
               <Card className="bg-surface-dim border-neutral-800">
                  <div className="flex items-center gap-3">
                     <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500"><Database size={20} /></div>
                     <div>
                        <p className="text-xs text-neutral-500 font-mono">VECTOR CHUNKS</p>
                        <p className="text-xl font-mono font-bold text-neutral-200">10,940</p>
                     </div>
                  </div>
               </Card>
            </div>

            <h3 className="text-lg font-medium text-neutral-300 mt-8">Active Collections</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {MOCK_COLLECTIONS.map((col) => (
                <Card key={col.id} className="hover:border-cyan-500/30 transition-colors group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-neutral-800 rounded group-hover:text-cyan-400 transition-colors">
                        <Book size={20} />
                      </div>
                      <div>
                        <h4 className="font-bold text-neutral-200">{col.name}</h4>
                        <div className="flex gap-2 text-xs text-neutral-500 font-mono">
                           <span>{col.docCount} DOCS</span>
                           <span>•</span>
                           <span>{col.chunkCount} CHUNKS</span>
                        </div>
                      </div>
                    </div>
                    {col.status === 'indexing' && (
                       <Badge variant="amber">Indexing</Badge>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-1">
                      {col.topics.map(topic => (
                        <span key={topic} className="px-1.5 py-0.5 rounded text-[10px] bg-neutral-800 text-neutral-400 border border-neutral-700">
                           #{topic}
                        </span>
                      ))}
                    </div>
                    
                    {col.status === 'indexing' && (
                       <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                             <span>Indexing Progress</span>
                             <span>45%</span>
                          </div>
                          <ProgressBar value={45} colorClass="bg-amber-500" />
                       </div>
                    )}

                    <div className="pt-3 border-t border-neutral-800 text-xs text-neutral-600 font-mono flex justify-between">
                       <span>Last Ingested: {col.lastIngested}</span>
                       <button className="hover:text-cyan-400 transition-colors">View Docs →</button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'SEARCH' && (
          <div className="max-w-4xl mx-auto space-y-8 mt-4">
             <div className="relative">
               <input 
                 type="text" 
                 placeholder="Search across all knowledge bases (semantic & keyword)..."
                 className="w-full bg-surface-raised border border-neutral-700 rounded-xl px-5 py-4 pl-12 text-neutral-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
               />
               <Search className="absolute left-4 top-4.5 text-neutral-500" size={20} />
               <div className="absolute right-4 top-4 flex gap-2">
                 <span className="text-xs px-2 py-1 bg-neutral-800 rounded border border-neutral-700 text-neutral-400">⌘K</span>
               </div>
             </div>

             <div className="space-y-4 opacity-50 text-center py-12">
               <Database size={48} className="mx-auto text-neutral-800 mb-4" />
               <p className="text-neutral-500">Enter a query to retrieve semantically relevant chunks from the vector store.</p>
             </div>
          </div>
        )}

      </div>
    </div>
  );
};

import { Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout/Layout';
import { DocumentsPage } from '@/pages/DocumentsPage';
import { ChatPage } from '@/pages/ChatPage';
import { StatusPage } from '@/pages/StatusPage';
import { SettingsPage } from '@/pages/SettingsPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DocumentsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
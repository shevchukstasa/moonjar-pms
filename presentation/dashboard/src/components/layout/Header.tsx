import { useAuthStore } from '@/stores/authStore';
import { Avatar } from '@/components/ui/Avatar';
import { DropdownMenu } from '@/components/ui/DropdownMenu';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import apiClient from '@/api/client';

export function Header() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await apiClient.post('/auth/logout'); } catch {}
    logout();
    navigate('/login');
  };

  return (
    <header className="flex h-16 items-center justify-between border-b bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <button className="relative rounded-full p-2 text-gray-400 hover:bg-gray-100" aria-label="Notifications"><Bell size={20} /></button>
        {user && <DropdownMenu trigger={<Avatar name={user.name} className="cursor-pointer" />} items={[{ label: user.name, onClick: () => {} }, { label: 'Logout', onClick: handleLogout }]} />}
      </div>
    </header>
  );
}

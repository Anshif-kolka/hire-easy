/* eslint-disable no-unused-vars */
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Users, GitCompare, Mail } from 'lucide-react';
import clsx from 'clsx';

const SidebarItem = ({ icon: Icon, label, to, active }) => (
  <Link
    to={to}
    className={clsx(
      "flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md transition-colors",
      active 
        ? "bg-slate-100 text-slate-900" 
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    )}
  >
    <Icon size={18} />
    {label}
  </Link>
);

const Layout = ({ children }) => {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-100">
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Briefcase className="text-slate-900" />
            Hire Easy
          </h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          <SidebarItem 
            icon={LayoutDashboard} 
            label="Dashboard" 
            to="/" 
            active={location.pathname === '/'} 
          />
          <SidebarItem 
            icon={Briefcase} 
            label="Jobs" 
            to="/jobs" 
            active={location.pathname.startsWith('/jobs')} 
          />
          <SidebarItem 
            icon={Users} 
            label="Candidates" 
            to="/candidates" 
            active={location.pathname.startsWith('/candidates')} 
          />
          <SidebarItem 
            icon={GitCompare} 
            label="Compare" 
            to="/compare" 
            active={location.pathname.startsWith('/compare')} 
          />
        </nav>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-medium text-xs">
              HR
            </div>
            <div className="text-sm">
              <p className="font-medium text-slate-900">Recruiter</p>
              <p className="text-slate-500 text-xs">admin@company.com</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
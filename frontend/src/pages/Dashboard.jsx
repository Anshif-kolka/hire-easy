/* eslint-disable no-unused-vars */
import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import JobForm from '../components/JobForm';
import { jobsApi, resumeApi } from '../api/client';
import { Briefcase, Users, FileText, Mail } from 'lucide-react';

const StatCard = ({ icon: Icon, label, value, subtext }) => (
  <div className="card p-6 flex items-start justify-between">
    <div>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <h3 className="text-2xl font-bold text-slate-900 mt-1">{value}</h3>
      {subtext && <p className="text-xs text-slate-400 mt-1">{subtext}</p>}
    </div>
    <div className="p-3 bg-slate-50 rounded-lg text-slate-600">
      <Icon size={20} />
    </div>
  </div>
);

const Dashboard = () => {
  const [stats, setStats] = useState({
    jobs: 0,
    candidates: 0,
    processed: 0
  });
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);

  const fetchStats = async () => {
    try {
      const jobsRes = await jobsApi.list();
      // In a real app, we'd have a stats endpoint. For now, just counting.
      // This is a simplification.
      setStats({
        jobs: jobsRes.data.length,
        candidates: 0, // We'd need to fetch all candidates to count them properly or add a stats endpoint
        processed: 0
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleEmailIngest = async () => {
    setIngesting(true);
    try {
      await resumeApi.triggerEmailIngest();
      alert('Email ingestion triggered successfully');
    } catch (err) {
      console.error(err);
      alert('Failed to trigger email ingestion');
    } finally {
      setIngesting(false);
    }
  };

  return (
    <Layout>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1">Overview of your hiring pipeline</p>
        </div>
        <button 
          onClick={handleEmailIngest}
          disabled={ingesting}
          className="btn-secondary"
        >
          <Mail size={16} />
          {ingesting ? 'Checking Inbox...' : 'Check Emails'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard 
          icon={Briefcase} 
          label="Active Jobs" 
          value={stats.jobs} 
          subtext="Open positions"
        />
        <StatCard 
          icon={Users} 
          label="Total Candidates" 
          value="--" 
          subtext="Across all jobs"
        />
        <StatCard 
          icon={FileText} 
          label="Resumes Processed" 
          value="--" 
          subtext="Last 30 days"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <JobForm onSuccess={fetchStats} />
        </div>
        
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Recent Activity</h3>
            <div className="space-y-4">
              <div className="text-sm text-slate-500 text-center py-4">
                No recent activity
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
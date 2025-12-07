import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { jobsApi } from '../api/client';
import { MapPin, Calendar, ChevronRight } from 'lucide-react';

const Jobs = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await jobsApi.list();
        setJobs(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, []);

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm('Delete this job and its embedding? This will NOT delete candidate rows.')) return;
    try {
      await jobsApi.delete(jobId);
      // Refresh jobs list
      const res = await jobsApi.list();
      setJobs(res.data);
    } catch (err) {
      console.error(err);
      alert('Failed to delete job');
    }
  };

  const handleDeleteJobCandidates = async (jobId) => {
    if (!window.confirm('Delete all candidates for this job and their resumes? This is permanent.')) return;
    try {
      await jobsApi.deleteCandidates(jobId);
      // Refresh jobs list and maybe candidates page will show none
      const res = await jobsApi.list();
      setJobs(res.data);
    } catch (err) {
      console.error(err);
      alert('Failed to delete candidates for job');
    }
  };

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Jobs</h1>
        <p className="text-slate-500 mt-1">Manage your open positions</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 card">
          <p className="text-slate-500">No jobs found. Create one from the dashboard.</p>
          <Link to="/" className="btn-primary inline-flex mt-4">
            Go to Dashboard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <div key={job.id} className="card p-6 hover:border-slate-300 transition-colors">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{job.job_title}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                    <span className="flex items-center gap-1">
                      <MapPin size={14} />
                      {job.location || 'Remote'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar size={14} />
                      Posted {new Date(job.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {job.required_skills.slice(0, 5).map((skill, i) => (
                      <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md font-medium">
                        {skill}
                      </span>
                    ))}
                    {job.required_skills.length > 5 && (
                      <span className="px-2 py-1 bg-slate-50 text-slate-400 text-xs rounded-md font-medium">
                        +{job.required_skills.length - 5} more
                      </span>
                    )}
                  </div>
                </div>
                <Link 
                  to={`/candidates?jobId=${job.id}`}
                  className="btn-secondary"
                >
                  View Candidates
                  <ChevronRight size={16} />
                </Link>
                <div className="flex flex-col gap-2 ml-3">
                  <button
                    onClick={() => handleDeleteJobCandidates(job.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete Candidates
                  </button>
                  <button
                    onClick={() => handleDeleteJob(job.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete Job
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default Jobs;
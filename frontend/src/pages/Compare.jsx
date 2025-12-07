import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { jobsApi, resumeApi } from '../api/client';
import { Check, X, Download } from 'lucide-react';

const Compare = () => {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidates, setSelectedCandidates] = useState([]);
  const [fullProfiles, setFullProfiles] = useState({});

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await jobsApi.list();
        setJobs(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchJobs();
  }, []);

  useEffect(() => {
    if (selectedJob) {
      const fetchCandidates = async () => {
        try {
          const res = await resumeApi.list(selectedJob);
          setCandidates(res.data);
          setSelectedCandidates([]);
          setFullProfiles({});
        } catch (err) {
          console.error(err);
        }
      };
      fetchCandidates();
    }
  }, [selectedJob]);

  const toggleCandidate = async (id) => {
    if (selectedCandidates.includes(id)) {
      setSelectedCandidates(prev => prev.filter(c => c !== id));
    } else {
      if (selectedCandidates.length >= 2) {
        alert("You can only compare 2 candidates at a time.");
        return;
      }
      setSelectedCandidates(prev => [...prev, id]);
      
      // Fetch full profile if not already loaded
      if (!fullProfiles[id]) {
        try {
          const res = await resumeApi.getFull(id);
          setFullProfiles(prev => ({ ...prev, [id]: res.data }));
        } catch (err) {
          console.error(err);
        }
      }
    }
  };

  const renderComparison = () => {
    if (selectedCandidates.length !== 2) return null;

    const c1 = fullProfiles[selectedCandidates[0]];
    const c2 = fullProfiles[selectedCandidates[1]];

    if (!c1 || !c2) return <div>Loading profiles...</div>;

    return (
      <div className="grid grid-cols-2 gap-8 mt-8">
      {[c1, c2].map((c) => (
          <div key={c.id} className="card p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <h3 className="text-xl font-bold text-slate-900">{c.name}</h3>
                <p className="text-slate-500 text-sm">{c.headline}</p>
              </div>
              <a 
                href={resumeApi.downloadUrl(c.id)} 
                target="_blank" 
                rel="noreferrer" 
                className="text-slate-400 hover:text-slate-900 ml-2"
                title="Download CV"
              >
                <Download size={18} />
              </a>
            </div>
            
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-slate-900 mb-2">Experience</h4>
                <p className="text-2xl font-bold text-slate-700">{c.total_experience_years} years</p>
                <div className="mt-2 space-y-2">
                  {c.experience.slice(0, 3).map((exp, i) => (
                    <div key={i} className="text-sm border-l-2 border-slate-200 pl-3">
                      <p className="font-medium">{exp.role}</p>
                      <p className="text-slate-500">{exp.company}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-slate-900 mb-2">Skills</h4>
                <div className="flex flex-wrap gap-2">
                  {c.skills.map((skill, i) => (
                    <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-slate-900 mb-2">Education</h4>
                {c.education.map((edu, i) => (
                  <div key={i} className="text-sm mb-1">
                    <p className="font-medium">{edu.degree}</p>
                    <p className="text-slate-500">{edu.institution}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Compare Candidates</h1>
        <p className="text-slate-500 mt-1">Side-by-side comparison</p>
      </div>

      <div className="mb-6">
        <label className="label">Select Job</label>
        <select 
          className="input-field w-full md:w-1/3"
          value={selectedJob}
          onChange={({ target }) => setSelectedJob(target.value)}
        >
          <option value="">Select a Job...</option>
          {jobs.map(job => (
            <option key={job.id} value={job.id}>{job.job_title}</option>
          ))}
        </select>
      </div>

      {selectedJob && (
        <div className="mb-8">
          <h3 className="font-semibold text-slate-900 mb-3">Select 2 Candidates to Compare</h3>
          <div className="flex flex-wrap gap-3">
            {candidates.map(c => (
              <button
                key={c.id}
                onClick={() => toggleCandidate(c.id)}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-colors flex items-center gap-2 ${
                  selectedCandidates.includes(c.id)
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                }`}
              >
                {selectedCandidates.includes(c.id) ? <Check size={14} /> : null}
                {c.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {renderComparison()}
    </Layout>
  );
};

export default Compare;
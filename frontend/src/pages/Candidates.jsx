import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import { jobsApi, resumeApi, rankingApi } from '../api/client';
import { Search, Filter, Download, Star, Github, Linkedin, Globe } from 'lucide-react';
import clsx from 'clsx';

const Candidates = () => {
  const [searchParams] = useSearchParams();
  const jobIdParam = searchParams.get('jobId');
  
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(jobIdParam || '');
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ranking, setRanking] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [rankingDetails, setRankingDetails] = useState({});

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await jobsApi.list();
        setJobs(res.data);
        if (!selectedJob && res.data.length > 0) {
          setSelectedJob(res.data[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchJobs();
  }, [selectedJob]);

  useEffect(() => {
    if (selectedJob) {
      fetchCandidates(selectedJob);
    }
  }, [selectedJob]);

  const fetchCandidates = async (jobId) => {
    setLoading(true);
    try {
      // First try to get ranked results
      try {
        const rankRes = await rankingApi.getRankings(jobId);
        if (rankRes.data && rankRes.data.rankings && rankRes.data.rankings.length > 0) {
          setCandidates(rankRes.data.rankings);
          return;
        }
      } catch {
        // Ignore if no rankings yet
      }

      // Fallback to raw list
      const res = await resumeApi.list(jobId);
      setCandidates(res.data.map(c => ({
        ...c,
        candidate_id: c.id, // Normalize ID
        overall_score: 0 // Default score
      })));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRankingDetail = async (candidateId) => {
    if (!selectedJob) return;
    try {
      const res = await rankingApi.getCandidateScore(selectedJob, candidateId);
      // Expected response is a ScoreReport-like object
      setRankingDetails(prev => ({ ...prev, [candidateId]: res.data }));
    } catch (err) {
      console.error('Failed to fetch ranking details', err);
    }
  };

  const toggleExpand = async (candidate) => {
    const cid = candidate.candidate_id || candidate.id;
    if (expandedId === cid) {
      setExpandedId(null);
      return;
    }

    setExpandedId(cid);
    if (!rankingDetails[cid]) {
      await fetchRankingDetail(cid);
    }
  };

  const handleDeleteCandidate = async (candidateId) => {
    if (!window.confirm('Delete this candidate and their resume permanently?')) return;
    try {
      await resumeApi.delete(candidateId);
      // Refresh list
      if (selectedJob) fetchCandidates(selectedJob);
    } catch (err) {
      console.error(err);
      alert('Failed to delete candidate');
    }
  };

  const handleRank = async () => {
    if (!selectedJob) return;
    setRanking(true);
    try {
      await rankingApi.getRankings(selectedJob, true); // force_refresh = true
      await fetchCandidates(selectedJob);
    } catch (err) {
      console.error(err);
      alert('Failed to rank candidates');
    } finally {
      setRanking(false);
    }
  };

  return (
    <Layout>
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Candidates</h1>
          <p className="text-slate-500 mt-1">Review and screen applicants</p>
        </div>
        <div className="flex gap-3">
          <select 
            className="input-field w-64"
            value={selectedJob}
            onChange={({ target }) => setSelectedJob(target.value)}
          >
            <option value="">Select a Job...</option>
            {jobs.map(job => (
              <option key={job.id} value={job.id}>{job.job_title}</option>
            ))}
          </select>
          <button 
            onClick={handleRank}
            disabled={ranking || !selectedJob}
            className="btn-primary"
            title="Force re-rank all candidates (LLM will be invoked)"
          >
            {ranking ? 'Ranking...' : 'Rank Candidates'}
          </button>
          <button
            onClick={async () => {
              if (!selectedJob) return;
              try {
                // Trigger background precompute and then refresh cached results
                await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/ranking/${selectedJob}/refresh`, { method: 'POST' });
                // Give the background job a short moment then fetch cached rankings
                setTimeout(() => fetchCandidates(selectedJob), 1200);
              } catch (err) {
                console.error('Failed to start background ranking', err);
                alert('Failed to start background ranking');
              }
            }}
            className="btn-secondary"
            title="Precompute rankings in background and cache results"
          >
            Precompute Rankings
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading candidates...</div>
      ) : candidates.length === 0 ? (
        <div className="text-center py-12 card">
          <p className="text-slate-500">No candidates found for this job.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((candidate) => (
            <div key={candidate.candidate_id} className="card p-6 hover:border-slate-300 transition-colors">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-slate-900 cursor-pointer" onClick={() => toggleExpand(candidate)}>{candidate.name || candidate.candidate_name}</h3>
                    {candidate.overall_score > 0 && (
                      <span className={clsx(
                        "px-2 py-0.5 text-xs font-bold rounded-full",
                        candidate.overall_score >= 80 ? "bg-green-100 text-green-700" :
                        candidate.overall_score >= 60 ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      )}>
                        {Math.round(candidate.overall_score)}% Match
                      </span>
                    )}
                  </div>
                  <p className="text-slate-500 text-sm mt-1">{candidate.headline || 'No headline'}</p>
                  
                  <div className="mt-4 flex flex-wrap gap-2">
                    {(candidate.skills || candidate.matched_skills || []).slice(0, 8).map((skill, i) => (
                      <span key={i} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md font-medium">
                        {skill}
                      </span>
                    ))}
                  </div>

                  <div className="mt-4 flex gap-4">
                    {candidate.github_url && (
                      <a href={candidate.github_url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-900">
                        <Github size={18} />
                      </a>
                    )}
                    {candidate.linkedin_url && (
                      <a href={candidate.linkedin_url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-blue-700">
                        <Linkedin size={18} />
                      </a>
                    )}
                    {candidate.portfolio_url && (
                      <a href={candidate.portfolio_url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-900">
                        <Globe size={18} />
                      </a>
                    )}
                    <a 
                      href={resumeApi.downloadUrl(candidate.candidate_id || candidate.id)} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="text-slate-400 hover:text-slate-900"
                      title="Download CV"
                    >
                      <Download size={18} />
                    </a>
                    <button
                      onClick={() => handleDeleteCandidate(candidate.candidate_id || candidate.id)}
                      className="ml-2 text-red-500 hover:text-red-700 text-sm"
                      title="Delete candidate"
                    >
                      Delete
                    </button>
                  </div>
                  {/* Expanded details */}
                  {expandedId === (candidate.candidate_id || candidate.id) && (
                    <div className="mt-4 p-4 bg-slate-50 border border-slate-100 rounded-md">
                      {rankingDetails[expandedId] ? (
                        <div className="space-y-3 text-sm text-slate-700">
                          <div>
                            <strong>Overall:</strong> {Math.round(rankingDetails[expandedId].overall_score || 0)}%
                          </div>
                          <div>
                            <strong>Skill Match:</strong> {Math.round(rankingDetails[expandedId].skill_match_score || 0)}%
                            {' • '}
                            <strong>Experience:</strong> {Math.round(rankingDetails[expandedId].experience_match_score || 0)}%
                          </div>
                          {rankingDetails[expandedId].matched_skills && rankingDetails[expandedId].matched_skills.length > 0 && (
                            <div>
                              <strong>Matched Skills:</strong>
                              <div className="mt-1 flex flex-wrap gap-2">
                                {rankingDetails[expandedId].matched_skills.map((s, i) => (
                                  <span key={i} className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-md">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {rankingDetails[expandedId].missing_skills && rankingDetails[expandedId].missing_skills.length > 0 && (
                            <div>
                              <strong>Missing Skills:</strong>
                              <div className="mt-1 flex flex-wrap gap-2">
                                {rankingDetails[expandedId].missing_skills.map((s, i) => (
                                  <span key={i} className="px-2 py-1 bg-red-50 text-red-700 text-xs rounded-md">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {rankingDetails[expandedId].strengths && rankingDetails[expandedId].strengths.length > 0 && (
                            <div>
                              <strong>Strengths:</strong>
                              <ul className="list-disc ml-5 mt-1 text-slate-700">
                                {rankingDetails[expandedId].strengths.map((s, i) => <li key={i}>{s}</li>)}
                              </ul>
                            </div>
                          )}
                          {rankingDetails[expandedId].weaknesses && rankingDetails[expandedId].weaknesses.length > 0 && (
                            <div>
                              <strong>Weaknesses:</strong>
                              <ul className="list-disc ml-5 mt-1 text-slate-700">
                                {rankingDetails[expandedId].weaknesses.map((s, i) => <li key={i}>{s}</li>)}
                              </ul>
                            </div>
                          )}
                          {rankingDetails[expandedId].reasoning && (
                            <div>
                              <strong>Reasoning:</strong>
                              <p className="mt-1 text-slate-600">{rankingDetails[expandedId].reasoning}</p>
                            </div>
                          )}
                          {rankingDetails[expandedId].recommendation && (
                            <div>
                              <strong>Recommendation:</strong>
                              <p className="mt-1 font-semibold text-slate-900">{rankingDetails[expandedId].recommendation}</p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-slate-500">Loading details...</div>
                      )}
                    </div>
                  )}
                </div>

                <div className="text-right">
                  <div className="text-sm text-slate-500">
                    Experience: <span className="font-medium text-slate-900">{candidate.total_experience_years || 0} years</span>
                  </div>
                  {candidate.recommendation && (
                    <div className="mt-2 text-sm text-slate-600 max-w-xs italic">
                      "{candidate.recommendation}"
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
};

export default Candidates;
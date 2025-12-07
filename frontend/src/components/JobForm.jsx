import React, { useState } from 'react';
import { jobsApi } from '../api/client';
import { Loader2, CheckCircle } from 'lucide-react';

const JobForm = ({ onSuccess }) => {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await jobsApi.create({ description });
      setSuccess(true);
      setDescription('');
      if (onSuccess) onSuccess();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError('Failed to create job. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Create New Job</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="label" htmlFor="description">
            Job Description
          </label>
          <textarea
            id="description"
            rows={6}
            className="input-field resize-none"
            placeholder="Paste the full job description here..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
          <p className="text-xs text-slate-500 mt-1">
            The AI will automatically extract title, skills, and requirements.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-md border border-red-100">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-50 text-green-700 text-sm rounded-md border border-green-100 flex items-center gap-2">
            <CheckCircle size={16} />
            Job created successfully!
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading || !description.trim()}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Processing...
              </>
            ) : (
              'Create Job'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default JobForm;
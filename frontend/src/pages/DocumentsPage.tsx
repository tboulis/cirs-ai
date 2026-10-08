import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, FileText, Trash2, Search, ArrowLeft } from "lucide-react";
import { documentApi } from "../services/api";
import { Document } from "../types";
import { toast } from "react-hot-toast";
import { formatDistanceToNow } from "date-fns";

const DocumentsPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  // Fetch documents
  const {
    data: documents = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentApi.getDocuments({ processed_only: false }),
  });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await documentApi.uploadDocument(file, {
        title: file.name.replace(/\.[^/.]+$/, ""),
        description: `Uploaded ${file.type} document`,
      });
      toast.success("Document uploaded successfully");
      refetch();
    } catch (error) {
      toast.error(`Upload failed: ${error}`);
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const handleProcessDocument = async (documentId: number) => {
    try {
      await documentApi.processDocument(documentId);
      toast.success("Document processing started");
      refetch();
    } catch (error) {
      toast.error(`Processing failed: ${error}`);
    }
  };

  const handleDeleteDocument = async (documentId: number) => {
    if (!window.confirm("Are you sure you want to delete this document?"))
      return;

    try {
      await documentApi.deleteDocument(documentId);
      toast.success("Document deleted successfully");
      refetch();
    } catch (error) {
      toast.error(`Delete failed: ${error}`);
    }
  };

  const filteredDocuments = documents.filter(
    (doc) =>
      doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-secondary-50">
      {/* Top navigation bar */}
      <header className="bg-white border-b border-secondary-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.history.back()}
              className="btn-ghost p-2"
              title="Back"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>

            <FileText className="w-6 h-6 text-primary-600" />
            <h1 className="text-lg font-semibold text-secondary-900">
              Document Management
            </h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">
            Document Management
          </h1>
          <p className="text-secondary-600 mt-2">
            Upload and manage documents for AI-powered search and analysis
          </p>
        </div>

        {/* Upload section */}
        <div className="card p-6 mb-8">
          <h2 className="text-xl font-semibold text-secondary-900 mb-4">
            Upload Document
          </h2>

          <div className="border-2 border-dashed border-secondary-300 rounded-lg p-8 text-center">
            <Upload className="w-12 h-12 text-secondary-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-secondary-900 mb-2">
              Choose files to upload
            </h3>
            <p className="text-secondary-600 mb-4">
              Supports PDF, DOCX, TXT, and MD files up to 10MB
            </p>

            <label className="btn-primary cursor-pointer">
              {isUploading ? "Uploading..." : "Browse Files"}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </label>
          </div>
        </div>

        {/* Search and filters */}
        <div className="card p-4 mb-6">
          <div className="flex items-center space-x-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-secondary-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10"
              />
            </div>

            <button className="btn-secondary">Filter</button>
          </div>
        </div>

        {/* Documents list */}
        <div className="card">
          <div className="px-6 py-4 border-b border-secondary-200">
            <h2 className="text-lg font-semibold text-secondary-900">
              Documents ({filteredDocuments.length})
            </h2>
          </div>

          {isLoading ? (
            <div className="p-8 text-center">
              <div className="spinner mx-auto mb-4"></div>
              <p className="text-secondary-500">Loading documents...</p>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-secondary-300 mx-auto mb-4" />
              <p className="text-secondary-500">
                {searchQuery
                  ? "No documents match your search"
                  : "No documents uploaded yet"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-secondary-200">
              {filteredDocuments.map((document) => (
                <DocumentRow
                  key={document.id}
                  document={document}
                  onProcess={() => handleProcessDocument(document.id)}
                  onDelete={() => handleDeleteDocument(document.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Document row component
interface DocumentRowProps {
  document: Document;
  onProcess: () => void;
  onDelete: () => void;
}

const DocumentRow: React.FC<DocumentRowProps> = ({
  document,
  onProcess,
  onDelete,
}) => {
  const formatFileSize = (bytes: number) => {
    const sizes = ["Bytes", "KB", "MB", "GB"];
    if (bytes === 0) return "0 Bytes";
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="p-6 hover:bg-secondary-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-start space-x-4">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <FileText className="w-5 h-5 text-primary-600" />
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-secondary-900 truncate">
              {document.title || document.original_filename}
            </h3>
            <p className="text-sm text-secondary-500 truncate">
              {document.original_filename}
            </p>

            <div className="flex items-center space-x-4 mt-2 text-xs text-secondary-400">
              <span>{formatFileSize(document.file_size)}</span>
              <span>{document.file_type.toUpperCase()}</span>
              <span>
                Uploaded{" "}
                {formatDistanceToNow(new Date(document.uploaded_at), {
                  addSuffix: true,
                })}
              </span>
              {document.processed && (
                <span className="text-success-600 font-medium">
                  Processed ({document.chunk_count} chunks)
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onDelete}
            className="btn-ghost p-2 text-error-500 hover:bg-error-50"
            title="Delete document"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentsPage;

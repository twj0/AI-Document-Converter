// frontend/src/components/FileUploader.tsx (Corrected Version)
import React, { useState } from 'react';
import { FilePond, registerPlugin } from 'react-filepond';

import 'filepond/dist/filepond.min.css';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';

registerPlugin(FilePondPluginFileValidateType);

const UPLOAD_URL = "http://127.0.0.1:8000/api/v1/tasks/upload";

interface FileUploaderProps {
  onUploadSuccess: (task: { id: string }) => void;
}

const FileUploader: React.FC<FileUploaderProps> = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState<any[]>([]);

  return (
    <div className="w-full text-slate-300">
      <FilePond
        files={files}
        onupdatefiles={setFiles}
        allowMultiple={true}
        maxFiles={10}
        server={{
          process: (fieldName, file, metadata, load, error, progress, abort) => {
            const formData = new FormData();
            formData.append("file", file, file.name);
            const extension = file.name.split('.').pop()?.toLowerCase() || '';
            let taskType = '';
            if (['ppt', 'pptx'].includes(extension)) {
              taskType = 'ppt_to_pdf';
            } else if (['doc', 'docx', 'pdf'].includes(extension)) {
              taskType = `${extension}_to_markdown`;
            } else {
              error('Unsupported file type');
              return;
            }
            formData.append('task_type', taskType);
            formData.append('subject', 'General');
            const request = new XMLHttpRequest();
            request.open('POST', UPLOAD_URL);
            request.upload.onprogress = (e) => {
              progress(e.lengthComputable, e.loaded, e.total);
            };
            request.onload = () => {
              if (request.status >= 200 && request.status < 300) {
                const response = JSON.parse(request.responseText);
                load(response.id);
                onUploadSuccess(response);
              } else {
                error('Upload failed');
                toast.error(`Upload failed for ${file.name}.`);
              }
            };
            request.onerror = () => {
              error('Upload failed');
              toast.error(`Network error during upload for ${file.name}.`);
            };
            request.send(formData);
            return {
              abort: () => {
                request.abort();
                abort();
              },
            };
          },
        }}
        name="file"
        labelIdle='Drag & Drop your files or <span class="filepond--label-action">Browse</span>'
        // --- THIS IS THE CORRECTED LINE ---
        acceptedFileTypes={[
          'application/pdf',
          'application/msword', // for .doc
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // for .docx
          'application/vnd.ms-powerpoint', // for .ppt
          'application/vnd.openxmlformats-officedocument.presentationml.presentation' // for .pptx
        ]}
      />
    </div>
  );
};

import { toast } from 'sonner';

export default FileUploader;
// Custom JavaScript for Microcosting Analysis Tool

// Function to initialize tooltips
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Function to show a notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.role = 'alert';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Function to confirm action
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Function to toggle loading state of a button
function toggleButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Loading...
        `;
    } else {
        button.disabled = false;
        // Restore original text (this is a simplified version)
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
        }
    }
}

// Function to format numbers as currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

// Function to format large numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Function to export table data to CSV
function exportTableToCSV(filename) {
    const table = document.getElementById('dataTable');
    if (!table) {
        showNotification('No table data found to export', 'warning');
        return;
    }

    let csv = [];
    const rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        const row = [];
        const cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            let text = cols[j].innerText || cols[j].textContent || '';
            // Escape quotes and wrap in quotes if contains comma, quote, or newline
            if (text.includes(',') || text.includes('"') || text.includes('\n')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            row.push(text);
        }
        csv.push(row.join(','));
    }

    // Download CSV file
    downloadFile(csv.join('\n'), filename, 'text/csv');
}

// Function to export table data to JSON
function exportTableToJSON(filename) {
    const table = document.getElementById('dataTable');
    if (!table) {
        showNotification('No table data found to export', 'warning');
        return;
    }

    const headers = [];
    const data = [];

    const headerRow = table.querySelector('thead tr');
    if (headerRow) {
        const headerCols = headerRow.querySelectorAll('th');
        headerCols.forEach(col => {
            headers.push(col.innerText || col.textContent || '');
        });
    }

    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const rowData = {};
        const cols = row.querySelectorAll('td');

        cols.forEach((col, index) => {
            const header = headers[index] || `Column_${index}`;
            rowData[header] = col.innerText || col.textContent || '';
        });

        data.push(rowData);
    });

    const jsonData = JSON.stringify(data, null, 2);
    downloadFile(jsonData, filename, 'application/json');
}

// Function to export full table data from server
async function exportFullTable(tableName, format) {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    toggleButtonLoading(button, true);

    try {
        let endpoint, filename, mimeType;

        switch (format.toLowerCase()) {
            case 'csv':
                endpoint = `/api/export/${tableName}/csv`;
                filename = `${tableName}.csv`;
                mimeType = 'text/csv';
                break;
            case 'excel':
                endpoint = `/api/export/${tableName}/excel`;
                filename = `${tableName}.xlsx`;
                mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                break;
            case 'json':
                endpoint = `/api/export/${tableName}/json`;
                filename = `${tableName}.json`;
                mimeType = 'application/json';
                break;
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }

        const response = await fetch(endpoint);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Export failed: ${response.status}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, filename, mimeType);

        showNotification(`Successfully exported ${tableName} as ${format.toUpperCase()}`, 'success');

    } catch (error) {
        console.error('Export error:', error);
        showNotification(`Export failed: ${error.message}`, 'error');
    } finally {
        toggleButtonLoading(button, false);
    }
}

// Function to download a blob
function downloadBlob(blob, filename, mimeType) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Function to download text content as file
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    downloadBlob(blob, filename, mimeType);
}

// Function to copy table data to clipboard
async function copyTableToClipboard() {
    const table = document.getElementById('dataTable');
    if (!table) {
        showNotification('No table data found to copy', 'warning');
        return;
    }

    let text = '';
    const rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        const cols = rows[i].querySelectorAll('td, th');
        const rowData = [];

        for (let j = 0; j < cols.length; j++) {
            rowData.push(cols[j].innerText || cols[j].textContent || '');
        }

        text += rowData.join('\t') + '\n';
    }

    try {
        await navigator.clipboard.writeText(text);
        showNotification('Table data copied to clipboard', 'success');
    } catch (error) {
        console.error('Clipboard error:', error);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Add any other initialization code here
    console.log('Microcosting Analysis Tool JavaScript initialized');
});

// Export functions to global scope
window.showNotification = showNotification;
window.confirmAction = confirmAction;
window.toggleButtonLoading = toggleButtonLoading;
window.formatCurrency = formatCurrency;
window.formatNumber = formatNumber;
window.exportTableToCSV = exportTableToCSV;
window.exportTableToJSON = exportTableToJSON;
window.exportFullTable = exportFullTable;
window.copyTableToClipboard = copyTableToClipboard;
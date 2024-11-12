import { fireEvent, waitFor } from '@testing-library/dom';
import '@testing-library/jest-dom';
import { settings } from '../../src/static/js/settings';

// Mock fetch
global.fetch = jest.fn();

describe('Settings Management', () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <input id="systemName" type="text">
            <input id="adminEmail" type="email">
            <select id="theme">
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System Default</option>
            </select>
            <button onclick="saveAllSettings()">Save</button>
        `;
        
        // Reset fetch mock
        fetch.mockReset();
    });

    test('loads settings successfully', async () => {
        const mockSettings = {
            system_name: 'Test System',
            admin_email: 'admin@test.com',
            theme: 'dark'
        };

        fetch.mockImplementationOnce(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockSettings)
            })
        );

        await loadSettings();

        expect(document.getElementById('systemName').value).toBe('Test System');
        expect(document.getElementById('adminEmail').value).toBe('admin@test.com');
        expect(document.getElementById('theme').value).toBe('dark');
    });

    test('saves settings successfully', async () => {
        const mockResponse = { status: 'success' };
        fetch.mockImplementationOnce(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            })
        );

        // Set form values
        document.getElementById('systemName').value = 'New System';
        document.getElementById('adminEmail').value = 'new@test.com';
        document.getElementById('theme').value = 'light';

        await saveAllSettings();

        expect(fetch).toHaveBeenCalledWith('/api/settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                system_name: 'New System',
                admin_email: 'new@test.com',
                theme: 'light'
            })
        });
    });

    test('handles theme changes', () => {
        const themeSelect = document.getElementById('theme');
        fireEvent.change(themeSelect, { target: { value: 'dark' } });

        expect(document.documentElement.classList.contains('dark')).toBe(true);
        expect(document.documentElement.classList.contains('light')).toBe(false);
    });

    test('tracks unsaved changes', () => {
        const systemNameInput = document.getElementById('systemName');
        fireEvent.change(systemNameInput, { target: { value: 'Changed Name' } });

        expect(hasUnsavedChanges).toBe(true);
        expect(document.querySelector('button').disabled).toBe(false);
    });
}); 
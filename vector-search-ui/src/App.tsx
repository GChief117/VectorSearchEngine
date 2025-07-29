// Typescript App
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  TextField,
  Button,
  Box,
  Typography,
  Link,
  InputAdornment,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
} from '@mui/material';
import { 
  Search as SearchIcon,
  Close as CloseIcon 
} from '@mui/icons-material';
import axios from 'axios';

// Create vintage Google theme
const vintageTheme = createTheme({
  palette: {
    mode: 'light',
    background: { 
      default: '#ffffff',
      paper: '#f5f5f5' 
    },
    text: { 
      primary: '#000000', 
      secondary: '#666666' 
    },
  },
  typography: { 
    fontFamily: 'Arial, sans-serif' 
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @font-face {
          font-family: 'Bank Gothic';
          src: url('/BankGothicRegular.ttf') format('truetype');
          font-weight: normal;
          font-style: normal;
          font-display: swap;
        }
      `,
    },
  },
});

const API_URL = process.env.REACT_APP_API_URL || '';

// Types
interface SearchResult {
  id: string;
  text: string;
  score: number;
}

const App: React.FC = () => {
  // State management
  const [query, setQuery] = useState<string>('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<{text: string, score: number}[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState<number>(-1);
  const [originalQuery, setOriginalQuery] = useState<string>('');
  const [showAboutDialog, setShowAboutDialog] = useState<boolean>(false);

  // Highlight matching text in suggestions
  const highlightMatch = (text: string, searchQuery: string): React.ReactNode => {
    const index = text.toLowerCase().indexOf(searchQuery.toLowerCase());
    if (index === -1) return text;
    
    const before = text.substring(0, index);
    const match = text.substring(index, index + searchQuery.length);
    const after = text.substring(index + searchQuery.length);
    
    return (
      <>
        {before}
        <span style={{ fontWeight: 600 }}>{match}</span>
        {after}
      </>
    );
  };

  // Handle navigation back to home
  const handleBackToHome = () => {
    setShowResults(false);
    setQuery('');
    setOriginalQuery('');
    setResults([]);
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
  };

  // Fetch search suggestions
  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    try {
      // In a real implementation, this would be a separate endpoint for suggestions
      const res = await axios.post(`${API_URL}/search`, { 
        query: searchQuery, 
        top_k: 5, 
        use_cache: true 
      });
      
      if (res.data.results && res.data.results.length > 0) {
        // Extract text snippets as suggestions - show full text with scores
        const suggestionTexts = res.data.results.map((r: SearchResult) => ({
          text: r.text,
          score: r.score
        }));
        setSuggestions(suggestionTexts);
        setShowSuggestions(true);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      // Fallback to mock suggestions for demonstration
      const mockSuggestions = [
        { text: `${searchQuery} in machine learning`, score: 0.95 },
        { text: `${searchQuery} tutorial`, score: 0.87 },
        { text: `${searchQuery} examples`, score: 0.82 },
        { text: `how to use ${searchQuery}`, score: 0.78 },
        { text: `${searchQuery} best practices`, score: 0.75 }
      ].slice(0, 4);
      setSuggestions(mockSuggestions);
      setShowSuggestions(true);
    }
  }, []);

  // Debounce function to avoid too many API calls
  const debounce = <T extends (...args: any[]) => any>(func: T, wait: number) => {
    let timeout: NodeJS.Timeout;
    return function executedFunction(...args: Parameters<T>) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  };

  // Debounced version of fetchSuggestions
  const debouncedFetchSuggestions = useMemo(
    () => debounce(fetchSuggestions, 300),
    [fetchSuggestions]
  );

  // Handle query change
  const handleQueryChange = (value: string) => {
    setQuery(value);
    setOriginalQuery(value);
    setSelectedSuggestionIndex(-1);
    if (value.trim()) {
      debouncedFetchSuggestions(value);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

// Handle suggestion selection
const handleSuggestionClick = async (suggestion: {text: string, score: number}) => {
  setQuery(suggestion.text);
  setOriginalQuery(suggestion.text);
  setShowSuggestions(false);
  setSuggestions([]);
  
  // Search with the suggestion text directly
  setLoading(true);
  try {
    console.log('Searching for:', suggestion.text);
    const res = await axios.post(`${API_URL}/search`, { 
      query: suggestion.text, 
      top_k: 10, 
      use_cache: true 
    });
    console.log('Search response:', res.data);
    setResults(res.data.results || []);
    setShowResults(true); // Show the results page
  } catch (err) {
    console.error('Search failed:', err);
    alert('Search failed. Please try again.');
  } finally {
    setLoading(false);
  }
};

  // Handle keyboard navigation for suggestions
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => {
          const newIndex = prev < suggestions.length - 1 ? prev + 1 : prev;
          if (newIndex >= 0) {
            setQuery(suggestions[newIndex].text);
          }
          return newIndex;
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => {
          const newIndex = prev > -1 ? prev - 1 : -1;
          if (newIndex === -1) {
            setQuery(originalQuery);
          } else {
            setQuery(suggestions[newIndex].text);
          }
          return newIndex;
        });
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSuggestionIndex >= 0) {
          handleSuggestionClick(suggestions[selectedSuggestionIndex]);
        } else {
          setShowSuggestions(false);
          handleSearch();
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedSuggestionIndex(-1);
        setQuery(originalQuery);
        break;
    }
  };

  // Handle clicking outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!(event.target as HTMLElement).closest('.search-container')) {
        setShowSuggestions(false);
        setSelectedSuggestionIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle ESC key to go back to main search
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.keyCode === 27 && showResults) {
        handleBackToHome();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [showResults]);

  // Handle search submission
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setShowSuggestions(false);
    setSuggestions([]);
    setSelectedSuggestionIndex(-1);
    
    try {
      const res = await axios.post(`${API_URL}/search`, { 
        query, 
        top_k: 10, 
        use_cache: true 
      });
      setResults(res.data.results || []);
      setShowResults(true);
    } catch (err) {
      console.error('Search failed:', err);
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };



  // Results page view
  if (showResults) {
    return (
      <ThemeProvider theme={vintageTheme}>
        <CssBaseline />
        <Box sx={{ minHeight: '100vh', bgcolor: '#ffffff' }}>
          {/* Header */}
          <Box sx={{ 
            borderBottom: '1px solid #e0e0e0', 
            p: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 3
          }}>
            <Box
              onClick={handleBackToHome}
              sx={{ 
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                '&:hover': {
                  opacity: 0.8,
                },
              }}
            >
              <Tooltip title="Back to home">
                <Typography 
                  sx={{ 
                    fontFamily: '"Bank Gothic", Arial, sans-serif',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    letterSpacing: '0.05em',
                    display: 'flex',
                    '& .g1': { color: '#4285f4' },
                    '& .g2': { color: '#ea4335' },
                    '& .g3': { color: '#fbbc04' },
                    '& .g4': { color: '#4285f4' },
                    '& .g5': { color: '#34a853' },
                    '& .g6': { color: '#ea4335' },
                    '& span': {
                      textShadow: `
                        -1px -1px 0 #000,
                        1px -1px 0 #000,
                        -1px 1px 0 #000,
                        1px 1px 0 #000,
                        2px 2px 3px rgba(0,0,0,0.3)
                      `
                    }
                  }}
                >
                  <span className="g1">V</span>
                  <span className="g2">E</span>
                  <span className="g3">C</span>
                  <span className="g4">T</span>
                  <span className="g5">O</span>
                  <span className="g6">R</span>
                  <span style={{ marginLeft: '0.2em' }} className="g1">S</span>
                  <span className="g2">E</span>
                  <span className="g3">A</span>
                  <span className="g4">R</span>
                  <span className="g5">C</span>
                  <span className="g6">H</span>
                </Typography>
              </Tooltip>
            </Box>
            <Box className="search-container" sx={{ position: 'relative', flex: 1, maxWidth: '600px' }}>
              <TextField
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onKeyDown={(e) => {
                  handleKeyDown(e);
                  if (e.key === 'Escape') {
                    setShowSuggestions(false);
                    setSelectedSuggestionIndex(-1);
                  }
                }}
                onFocus={() => query.trim() && suggestions.length > 0 && setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && selectedSuggestionIndex === -1) {
                    e.preventDefault();
                    setShowSuggestions(false);
                    handleSearch();
                  }
                }}
                variant="outlined"
                size="small"
                fullWidth
                placeholder="Search..."
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#9aa0a6', fontSize: 20 }} />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: showSuggestions ? '24px 24px 0 0' : '24px',
                    '& fieldset': { borderColor: '#dfe1e5' },
                    '&:hover fieldset': { borderColor: '#dfe1e5' },
                    '&.Mui-focused fieldset': { borderColor: '#4285f4' },
                  },
                }}
              />
              
              {/* Suggestions Dropdown for Results Page */}
              {showSuggestions && suggestions.length > 0 && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    backgroundColor: '#fff',
                    boxShadow: '0 4px 6px rgba(32,33,36,.28)',
                    borderRadius: '0 0 24px 24px',
                    zIndex: 1000,
                    maxHeight: '300px',
                    overflowY: 'auto',
                    border: '1px solid #dfe1e5',
                    borderTop: 'none',
                    animation: 'fadeIn 0.1s ease-in',
                    '@keyframes fadeIn': {
                      from: {
                        opacity: 0,
                        transform: 'translateY(-10px)',
                      },
                      to: {
                        opacity: 1,
                        transform: 'translateY(0)',
                      },
                    },
                    '&::-webkit-scrollbar': {
                      width: '8px',
                    },
                    '&::-webkit-scrollbar-track': {
                      background: '#f1f1f1',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      background: '#888',
                      borderRadius: '4px',
                    },
                    '&::-webkit-scrollbar-thumb:hover': {
                      background: '#555',
                    },
                  }}
                >
                  {suggestions.map((suggestion, index) => (
                    <Box
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      sx={{
                        padding: '8px 14px 8px 40px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        backgroundColor: selectedSuggestionIndex === index ? '#f8f9fa' : 'transparent',
                        '&:hover': {
                          backgroundColor: '#f8f9fa',
                        },
                        position: 'relative',
                      }}
                    >
                      <SearchIcon 
                        sx={{ 
                          position: 'absolute',
                          left: '12px',
                          color: '#70757a',
                          fontSize: 16 
                        }} 
                      />
                      <Typography
                        sx={{
                          fontSize: '14px',
                          color: '#000',
                          fontFamily: 'Arial, sans-serif',
                          flex: 1,
                          pr: 2,
                        }}
                      >
                        {highlightMatch(suggestion.text, query)}
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: '12px',
                          color: '#70757a',
                          fontFamily: 'Arial, sans-serif',
                        }}
                      >
                        {(suggestion.score * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
            <Button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              sx={{
                minWidth: 'auto',
                p: 1,
                color: '#4285f4',
                '&:hover': {
                  backgroundColor: 'rgba(66, 133, 244, 0.08)',
                },
              }}
            >
              <SearchIcon />
            </Button>
          </Box>

          {/* Results - Left Aligned */}
          <Box sx={{ maxWidth: '850px', py: 3, px: { xs: 2, md: 4 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '14px' }}>
                About {results.length} results
              </Typography>
              <Button
                onClick={handleBackToHome}
                sx={{
                  textTransform: 'none',
                  color: '#1a0dab',
                  '&:hover': {
                    textDecoration: 'underline',
                    backgroundColor: 'transparent',
                  },
                }}
              >
                New Search
              </Button>
            </Box>
            
            {results.map((result, index) => (
              <Box key={result.id} sx={{ mb: 4 }}>
                <Link 
                  href="#" 
                  sx={{ 
                    fontSize: '24px',
                    color: '#1a0dab',
                    textDecoration: 'none',
                    '&:hover': { textDecoration: 'underline' }
                  }}
                >
                  {result.text} - Score: {(result.score * 100).toFixed(1)}%
                </Link>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: '#006621',
                    fontSize: '16px',
                    mt: 0.5 
                  }}
                >
                  {result.id.substring(0, 40)}...
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: '#545454',
                    mt: 0.5,
                    lineHeight: 1.58,
                    fontSize: '16px' 
                  }}
                >
                  {result.text}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </ThemeProvider>
    );
  }

  // Main search page - vintage Google style - Upper region positioning
  return (
    <ThemeProvider theme={vintageTheme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: '#ffffff',
          position: 'relative'
        }}
      >
        {/* Centered content */}
        <Box sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          pb: 10 // Add padding bottom to account for footer
        }}>
          <Box sx={{ mb: 4, textAlign: 'center' }}>
          {/* Vintage Google-style logo with colors */}
          <Typography 
            sx={{ 
              fontFamily: '"Bank Gothic", Arial, sans-serif',
              fontSize: { xs: '2.5rem', md: '4rem' },
              fontWeight: 'bold',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              lineHeight: 1,
              mb: 3,
              display: 'flex',
              justifyContent: 'center',
              flexDirection: 'column',
              alignItems: 'center',
              '& .g1': { color: '#4285f4' },
              '& .g2': { color: '#ea4335' },
              '& .g3': { color: '#fbbc04' },
              '& .g4': { color: '#4285f4' },
              '& .g5': { color: '#34a853' },
              '& .g6': { color: '#ea4335' },
              '& span': {
                textShadow: `
                  -1px -1px 0 #000,
                  1px -1px 0 #000,
                  -1px 1px 0 #000,
                  1px 1px 0 #000,
                  2px 2px 4px rgba(0,0,0,0.3)
                `
              }
            }}
          >
            <Box sx={{ display: 'flex' }}>
              <span className="g1">V</span>
              <span className="g2">E</span>
              <span className="g3">C</span>
              <span className="g4">T</span>
              <span className="g5">O</span>
              <span className="g6">R</span>
              <span style={{ marginLeft: '0.3em' }} className="g1">S</span>
              <span className="g2">E</span>
              <span className="g3">A</span>
              <span className="g4">R</span>
              <span className="g5">C</span>
              <span className="g6">H</span>
            </Box>
            <Box sx={{ display: 'flex' }}>
              <span className="g1">E</span>
              <span className="g2">N</span>
              <span className="g3">G</span>
              <span className="g4">I</span>
              <span className="g5">N</span>
              <span className="g6">E</span>
            </Box>
          </Typography>
        </Box>

        <form onSubmit={handleSearch}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, position: 'relative' }}>
            <Box className="search-container" sx={{ position: 'relative', width: { xs: '90vw', sm: '584px' } }}>
              <TextField
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onKeyDown={(e) => {
                  handleKeyDown(e);
                  if (e.key === 'Escape') {
                    setShowSuggestions(false);
                    setSelectedSuggestionIndex(-1);
                  }
                }}
                onFocus={() => query.trim() && suggestions.length > 0 && setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                variant="outlined"
                fullWidth
                placeholder="Search..."
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#9aa0a6', fontSize: 20 }} />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: showSuggestions ? '24px 24px 0 0' : '24px',
                    backgroundColor: '#fff',
                    boxShadow: '0 2px 5px 1px rgba(64,60,67,.16)',
                    '&:hover': {
                      boxShadow: '0 2px 8px 1px rgba(64,60,67,.24)',
                    },
                    '& fieldset': { 
                      borderColor: 'transparent',
                    },
                    '&:hover fieldset': { 
                      borderColor: 'transparent',
                    },
                    '&.Mui-focused fieldset': { 
                      borderColor: 'transparent',
                    },
                  },
                  '& .MuiInputBase-input': {
                    padding: '12px 48px 12px 8px',
                  },
                }}
              />
              
              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    backgroundColor: '#fff',
                    boxShadow: '0 4px 6px rgba(32,33,36,.28)',
                    borderRadius: '0 0 24px 24px',
                    zIndex: 1000,
                    maxHeight: '300px',
                    overflowY: 'auto',
                    animation: 'fadeIn 0.1s ease-in',
                    '@keyframes fadeIn': {
                      from: {
                        opacity: 0,
                        transform: 'translateY(-10px)',
                      },
                      to: {
                        opacity: 1,
                        transform: 'translateY(0)',
                      },
                    },
                    '&::-webkit-scrollbar': {
                      width: '8px',
                    },
                    '&::-webkit-scrollbar-track': {
                      background: '#f1f1f1',
                    },
                    '&::-webkit-scrollbar-thumb': {
                      background: '#888',
                      borderRadius: '4px',
                    },
                    '&::-webkit-scrollbar-thumb:hover': {
                      background: '#555',
                    },
                  }}
                >
                  {suggestions.map((suggestion, index) => (
                    <Box
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      sx={{
                        padding: '12px 14px 12px 52px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        backgroundColor: selectedSuggestionIndex === index ? '#f8f9fa' : 'transparent',
                        '&:hover': {
                          backgroundColor: '#f8f9fa',
                        },
                        position: 'relative',
                      }}
                    >
                      <SearchIcon 
                        sx={{ 
                          position: 'absolute',
                          left: '16px',
                          color: '#70757a',
                          fontSize: 18 
                        }} 
                      />
                      <Typography
                        sx={{
                          fontSize: '16px',
                          color: '#000',
                          fontFamily: 'Arial, sans-serif',
                          flex: 1,
                          pr: 2,
                        }}
                      >
                        {highlightMatch(suggestion.text, query)}
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: '14px',
                          color: '#70757a',
                          fontFamily: 'Arial, sans-serif',
                        }}
                      >
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                type="submit"
                variant="contained"
                disabled={loading}
                sx={{
                  bgcolor: '#f8f9fa',
                  color: '#3c4043',
                  textTransform: 'none',
                  fontSize: '14px',
                  fontWeight: 400,
                  px: 2.5,
                  py: 1,
                  border: '1px solid #f8f9fa',
                  borderRadius: '4px',
                  boxShadow: 'none',
                  '&:hover': {
                    bgcolor: '#f8f9fa',
                    border: '1px solid #dadce0',
                    boxShadow: '0 1px 1px rgba(0,0,0,.1)',
                  },
                  '&:disabled': {
                    bgcolor: '#f8f9fa',
                    color: '#80868b',
                  },
                }}
              >
                Vector Search
              </Button>
              <Button
                onClick={() => setShowAboutDialog(true)}
                variant="contained"
                sx={{
                  bgcolor: '#f8f9fa',
                  color: '#3c4043',
                  textTransform: 'none',
                  fontSize: '14px',
                  fontWeight: 400,
                  px: 2.5,
                  py: 1,
                  border: '1px solid #f8f9fa',
                  borderRadius: '4px',
                  boxShadow: 'none',
                  '&:hover': {
                    bgcolor: '#f8f9fa',
                    border: '1px solid #dadce0',
                    boxShadow: '0 1px 1px rgba(0,0,0,.1)',
                  },
                }}
              >
                About
              </Button>
            </Box>
          </Box>
        </form>

        </Box>

        {/* Footer */}
        <Box sx={{ 
          position: 'absolute', 
          bottom: 0, 
          width: '100%',
          bgcolor: '#f2f2f2',
          borderTop: '1px solid #e4e4e4'
        }}>
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center',
            alignItems: 'center',
            gap: 3,
            px: 3,
            py: 2
          }}>
            <Link 
              href="#" 
              onClick={(e) => {
                e.preventDefault();
                setShowAboutDialog(true);
              }}
              sx={{ color: '#70757a', fontSize: '14px', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
            >
              About
            </Link>
            <Link href="#" sx={{ color: '#70757a', fontSize: '14px', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>
              How Search Works
            </Link>
            <Link href="https://github.com/GChief117" target="_blank" sx={{ color: '#70757a', fontSize: '14px', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}>
              GitHub
            </Link>
          </Box>
        </Box>

        {/* About Dialog */}
        <Dialog
          open={showAboutDialog}
          onClose={() => setShowAboutDialog(false)}
          maxWidth="md"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: '16px',
              boxShadow: '0 24px 48px rgba(0,0,0,.12)',
            }
          }}
        >
          <DialogTitle sx={{ 
            fontSize: '2rem',
            fontWeight: 'bold',
            pb: 0,
            textAlign: 'center',
            position: 'relative'
          }}>
            About Vector Search Engine
            <IconButton
              onClick={() => setShowAboutDialog(false)}
              sx={{ 
                color: '#5f6368',
                position: 'absolute',
                right: 8,
                top: 8
              }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ pt: 2, pb: 4 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: '600px', mx: 'auto' }}>
              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  What is Vector Search?
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  Vector search transforms text into mathematical representations (vectors) that capture semantic meaning. Unlike traditional keyword matching, it understands context and relationships between concepts, enabling more intelligent and accurate search results.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  How It Works
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  When you search for "car", vector search understands related concepts like "automobile", "vehicle", or "sedan". It measures similarity between concepts using mathematical distances, so even if exact keywords don't match, relevant results still appear based on meaning.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  Intelligent Similarity Scoring
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  Each result receives a similarity score (0-100%) indicating how closely it matches your query's meaning. Higher scores mean stronger conceptual relationships, helping you quickly identify the most relevant information.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  Key Advantages
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  • <strong>Natural Language Understanding:</strong> Ask questions conversationally<br/>
                  • <strong>Context-Aware Results:</strong> Finds information based on meaning, not just keywords<br/>
                  • <strong>Typo Tolerance:</strong> Understands intent despite spelling errors<br/>
                  • <strong>Concept Discovery:</strong> Surfaces related topics you hadn't considered
                </Typography>
              </Box>
            </Box>
          </DialogContent>
        </Dialog>

        {/* About Dialog */}
        <Dialog
          open={showAboutDialog}
          onClose={() => setShowAboutDialog(false)}
          maxWidth="md"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: '16px',
              boxShadow: '0 24px 48px rgba(0,0,0,.12)',
            }
          }}
        >
          <DialogTitle sx={{ 
            fontSize: '2rem',
            fontWeight: 'bold',
            pb: 0,
            textAlign: 'center',
            position: 'relative'
          }}>
            About Vector Search Engine
            <IconButton
              onClick={() => setShowAboutDialog(false)}
              sx={{ 
                color: '#5f6368',
                position: 'absolute',
                right: 8,
                top: 8
              }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ pt: 2, pb: 4 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: '600px', mx: 'auto' }}>
              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  What is Vector Search?
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  Vector search transforms text into mathematical representations (vectors) that capture semantic meaning. Unlike traditional keyword matching, it understands context and relationships between concepts, enabling more intelligent and accurate search results.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  How It Works
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  When you search for "car", vector search understands related concepts like "automobile", "vehicle", or "sedan". It measures similarity between concepts using mathematical distances, so even if exact keywords don't match, relevant results still appear based on meaning.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  Intelligent Similarity Scoring
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  Each result receives a similarity score (0-100%) indicating how closely it matches your query's meaning. Higher scores mean stronger conceptual relationships, helping you quickly identify the most relevant information.
                </Typography>
              </Box>

              <Box>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: '#000', textAlign: 'center' }}>
                  Key Advantages
                </Typography>
                <Typography sx={{ color: '#5f6368', lineHeight: 1.8, fontSize: '15px', textAlign: 'left' }}>
                  • <strong>Natural Language Understanding:</strong> Ask questions conversationally<br/>
                  • <strong>Context-Aware Results:</strong> Finds information based on meaning, not just keywords<br/>
                  • <strong>Typo Tolerance:</strong> Understands intent despite spelling errors<br/>
                  • <strong>Concept Discovery:</strong> Surfaces related topics you hadn't considered
                </Typography>
              </Box>
            </Box>
          </DialogContent>
        </Dialog>
      </Box>
    </ThemeProvider>
  );
};

export default App;
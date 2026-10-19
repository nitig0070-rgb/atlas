<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Report_copilot {
    public function ask($clientId, $message, $conversationId = NULL) {
        $url = getenv('AI_SERVICE_URL') ?: 'http://api:8000';
        $key = getenv('AI_SERVICE_API_KEY') ?: '';
        $payload = json_encode(['client_id'=>$clientId, 'message'=>$message, 'conversation_id'=>$conversationId]);
        $ch = curl_init($url . '/chat');
        curl_setopt_array($ch, [CURLOPT_POST=>TRUE, CURLOPT_RETURNTRANSFER=>TRUE, CURLOPT_HTTPHEADER=>['Content-Type: application/json', 'X-API-Key: ' . $key], CURLOPT_POSTFIELDS=>$payload, CURLOPT_CONNECTTIMEOUT=>3, CURLOPT_TIMEOUT=>25]);
        $response = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response === FALSE) return ['answer'=>'The Report Copilot is temporarily unavailable. Please try again or contact an analyst.'];
        $decoded = json_decode($response, TRUE);
        if ($status < 200 || $status >= 300) {
            // The API maps provider/configuration failures to safe public details.
            // The view escapes this string before rendering it.
            if (is_array($decoded) && isset($decoded['detail']) && is_string($decoded['detail'])) {
                return ['answer'=>$decoded['detail']];
            }
            return ['answer'=>'The Report Copilot is temporarily unavailable. Please try again or contact an analyst.'];
        }
        return is_array($decoded) && isset($decoded['answer']) ? $decoded : ['answer'=>'The Report Copilot is temporarily unavailable. Please try again or contact an analyst.'];
    }

    public function history($clientId, $conversationId) {
        if (!$conversationId) return [];
        $url = getenv('AI_SERVICE_URL') ?: 'http://api:8000';
        $key = getenv('AI_SERVICE_API_KEY') ?: '';
        $target = $url . '/conversations/' . rawurlencode($conversationId) . '/messages?client_id=' . rawurlencode($clientId);
        $ch = curl_init($target);
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER=>TRUE, CURLOPT_HTTPHEADER=>['X-API-Key: ' . $key], CURLOPT_CONNECTTIMEOUT=>3, CURLOPT_TIMEOUT=>8]);
        $response = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response === FALSE || $status < 200 || $status >= 300) return [];
        $decoded = json_decode($response, TRUE);
        return is_array($decoded) ? $decoded : [];
    }
}

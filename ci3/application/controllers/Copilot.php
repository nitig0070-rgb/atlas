<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Copilot extends CI_Controller {
    public function __construct() {
        parent::__construct();
        $this->load->library('Report_copilot');
    }

    public function index() {
        if ($this->input->get('demo_client', TRUE)) {
            $requested = $this->input->get('demo_client', TRUE);
            if (in_array($requested, ['C-01', 'C-02'], TRUE)) {
                if ($this->session->userdata('client_id') !== $requested) $this->session->unset_userdata('conversation_id');
                $this->session->set_userdata('client_id', $requested);
            }
        }
        $data['client_id'] = $this->session->userdata('client_id') ?: 'C-01';
        $data['result'] = $this->session->flashdata('result');
        $data['history'] = $this->report_copilot->history($data['client_id'], $this->session->userdata('conversation_id'));
        $this->load->view('copilot', $data);
    }

    public function chat() {
        $this->form_validation->set_rules('message', 'Message', 'required|max_length[4000]');
        if (!$this->form_validation->run()) { $this->session->set_flashdata('answer', 'Please enter a question of at most 4,000 characters.'); redirect('/copilot'); return; }
        $requested = $this->input->post('client_id', TRUE);
        if (in_array($requested, ['C-01', 'C-02'], TRUE)) {
            if ($this->session->userdata('client_id') !== $requested) $this->session->unset_userdata('conversation_id');
            $this->session->set_userdata('client_id', $requested);
        }
        $client = $this->session->userdata('client_id');
        $body = $this->report_copilot->ask($client, $this->input->post('message', TRUE), $this->session->userdata('conversation_id'));
        if (!empty($body['conversation_id'])) $this->session->set_userdata('conversation_id', $body['conversation_id']);
        $this->session->set_flashdata('result', $body);
        redirect('/copilot');
    }

    public function feedback() {
        $messageId = (int)$this->input->post('message_id');
        $conversationId = $this->input->post('conversation_id', TRUE);
        $rating = (int)$this->input->post('rating');
        if ($messageId > 0 && preg_match('/^[0-9a-f-]{36}$/i', $conversationId) && in_array($rating, [-1, 1], TRUE)) {
            $owner = $this->db->where('id', $conversationId)->where('client_id', $this->session->userdata('client_id'))->count_all_results('conversations');
            $message = $this->db->where('id', $messageId)->where('conversation_id', $conversationId)->where('role', 'assistant')->count_all_results('conversation_messages');
            if ($owner === 1 && $message === 1) $this->db->insert('feedback', ['conversation_id'=>$conversationId, 'message_id'=>$messageId, 'rating'=>$rating]);
        }
        redirect('/copilot');
    }
}

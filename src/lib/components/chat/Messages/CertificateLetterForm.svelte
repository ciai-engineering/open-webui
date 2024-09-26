<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { DateInput } from 'date-picker-svelte';
	import Textfield from '@smui/textfield';
	import { createEventDispatcher } from 'svelte';
	import { user } from '$lib/stores';
	import { submitHRDocuments } from '$lib/apis/chats';
	import { toast } from 'svelte-sonner';
	// import Select, { Option } from '@smui/select';

	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	let language = '';
	let purpose = '';
	let type = '';
	let addressee = '';
	const letters = [
		'Job Letter',
		'Salary Certificate',
		'Bank Letter',
		'Salary Transfer Letter',
		'NOC (No Objection Certificate)',
		'Golden Visa Application Letter'
	];

	$: if (type) {
		addressee = '';
		purpose = '';
		language = '';
	}

	const dateFormatter = (val) => {
		const date = val ? new Date(val) : new Date();
		// const dateString = date.toDateString().split(' ')
		// dateString.splice(0,1)
		// return `${dateString[1]} ${dateString[0]} ${dateString[2]}`
		const months = [
			'January',
			'February',
			'March',
			'April',
			'May',
			'June',
			'July',
			'August',
			'September',
			'October',
			'November',
			'December'
		];

		const day = date.getDate();
		const month = months[date.getMonth()];
		const year = date.getFullYear();

		// 添加后缀
		let suffix = 'th';
		if (day % 10 === 1 && day !== 11) {
			suffix = 'st';
		} else if (day % 10 === 2 && day !== 12) {
			suffix = 'nd';
		} else if (day % 10 === 3 && day !== 13) {
			suffix = 'rd';
		}

		return `${month} ${day}${suffix}, ${year}`;
	};
	const handleConfirm = () => {
		// if (!$user.extra_sso) {
		// 	toast.error('User type error. Only supports users login with outlook account.');
		// 	return;
		// }
		// const ssoData = JSON.parse($user.extra_sso);
		const ssoData = JSON.parse(
			'{"emp_id": "AI40118", "email": "yewang.xie@mbzuai.ac.ae", "emp_type": "Staff", "first_name": "Yewang", "last_name": "Xie", "job_title": "Senior Frontend Engineer ", "department": "CIAI", "new_department": "CIAI", "line_manager_name": "Yue Peng", "line_manager_email": "yue.peng@mbzuai.ac.ae", "contract_type": "Fixed Term Contract", "access_token": "eyJ0eXAiOiJKV1QiLCJub25jZSI6IkFhOXRXRm9KZGJMZ3Fad1ZETzJrMEJ4VS03b1ljeWYxMmNmVTZkbEo4VlkiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik1jN2wzSXo5M2c3dXdnTmVFbW13X1dZR1BrbyIsImtpZCI6Ik1jN2wzSXo5M2c3dXdnTmVFbW13X1dZR1BrbyJ9.eyJhdWQiOiIwMDAwMDAwMy0wMDAwLTAwMDAtYzAwMC0wMDAwMDAwMDAwMDAiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9jOTMyNzJkMy0xYjA3LTRiM2QtYTNiNi0xOWIzNGE5NzM5MTUvIiwiaWF0IjoxNzI3MTc5NTc3LCJuYmYiOjE3MjcxNzk1NzcsImV4cCI6MTcyNzE4Mzg0NywiYWNjdCI6MCwiYWNyIjoiMSIsImFpbyI6IkFUUUF5LzhZQUFBQUlscFFybm1uc2VNblMvZW9CSUtOTmM4Q0VRWG5iOEZmdEE5Vkd6TS9XRVdxa3hkYVhva0NvMkw3c0V2TGIvb2wiLCJhbXIiOlsicHdkIl0sImFwcF9kaXNwbGF5bmFtZSI6IkNJQUktUkFHIiwiYXBwaWQiOiIyYjBlNTBmNi02OTM3LTRhMzItOTUwMS05NGJmNzM1N2U4ODMiLCJhcHBpZGFjciI6IjEiLCJmYW1pbHlfbmFtZSI6IlhpZSIsImdpdmVuX25hbWUiOiJZZXdhbmciLCJpZHR5cCI6InVzZXIiLCJpcGFkZHIiOiI1LjE5NS4wLjE0NSIsIm5hbWUiOiJZZXdhbmcgWGllIiwib2lkIjoiYjQ2YjlmMjYtYmRkNC00YjYzLWJmZjItY2NhODRmOTUyNzJmIiwib25wcmVtX3NpZCI6IlMtMS01LTIxLTgwNTc2MzEwMy0yNzk4Njg3MzQ1LTY1MzAyMTc3OS01NzIyIiwicGxhdGYiOiI1IiwicHVpZCI6IjEwMDMyMDAzNkJGQTREQzQiLCJyaCI6IjAuQVVnQTAzSXl5UWNiUFV1anRobXpTcGM1RlFNQUFBQUFBQUFBd0FBQUFBQUFBQUFMQWFzLiIsInNjcCI6IkRpcmVjdG9yeS5SZWFkLkFsbCBNYWlsLlJlYWQgTWFpbC5TZW5kIFVzZXIuUmVhZCBVc2VyLlJlYWRCYXNpYy5BbGwgcHJvZmlsZSBvcGVuaWQgZW1haWwiLCJzaWduaW5fc3RhdGUiOlsiaW5rbm93bm50d2siLCJrbXNpIl0sInN1YiI6IjdXVWFCazFKZlJKdnNJVXc3cW5iZXdwWVFrVUdLelBpdFBod1NXUURUSmMiLCJ0ZW5hbnRfcmVnaW9uX3Njb3BlIjoiRVUiLCJ0aWQiOiJjOTMyNzJkMy0xYjA3LTRiM2QtYTNiNi0xOWIzNGE5NzM5MTUiLCJ1bmlxdWVfbmFtZSI6Illld2FuZy5YaWVAbWJ6dWFpLmFjLmFlIiwidXBuIjoiWWV3YW5nLlhpZUBtYnp1YWkuYWMuYWUiLCJ1dGkiOiI5b0U2RGR1VTBVMmZ1VEtVMDQ0WEFBIiwidmVyIjoiMS4wIiwid2lkcyI6WyJiNzlmYmY0ZC0zZWY5LTQ2ODktODE0My03NmIxOTRlODU1MDkiXSwieG1zX2lkcmVsIjoiMSAyIiwieG1zX3N0Ijp7InN1YiI6InV4dmdvQVh3cm1fOWV6LWFsRXY0RGY2T2dRRk5yTkpJSE5UOV9UNkozcTQifSwieG1zX3RjZHQiOjE1Nzc2OTQwNjd9.BwxSbSFLASVw07X4bECrXPhidzG-D-L3PtEUZzCcaWX6ELS-h7tMnsISPEBGWYUAJyId20GBXfbtUGHsHkl14WJZlS4zkFkjYaNVPgUB4VAWy6ChP4qDBJDr5-M5SulJlBacX6JttQqn6ozxKyEap_kd36t_L90LwPsO46ThXh4ZCi2uRCtIANBcCZlh48O-Rp3oBq6--GXPWMObvTRzOfZVLuxsUmQPRwyHlpOb0jxxHNMGUFbB2figQUvryGlyZCBlXLWRQxd7nG_3HiQ8HADxKSBN6gLM_sIQ7O4NZ-f2IJDOEfr5BvhymygfcsRrSsyFdgAt920E0VL9XdfyrQ"}'
		);
		const formData = {
			name: $user.name,
			employee_id: ssoData.emp_id,
			job_title: ssoData.job_title,
			dept: ssoData.department,
			type_of_document: letters.findIndex((el) => el == type) + 1 ?? undefined,
			purpose,
			language,
			addressee,
			email: $user.email,
			date: dateFormatter()
		};
		// dispatch('confirm', formData);
		submitHRDocuments(localStorage.token, formData)
			.then((res) => {
				dispatch('confirm', {
					...formData,
					documentName: type
				});
				show = false;
			})
			.catch((err) => {
				toast(err.detail + ' Submission failed.');
				return;
			});
	};
</script>

<!-- <Modal size="lg" bind:show> -->
<div class="w-7/12 bg-[#ffffffdd] dark:bg-[#ffffff80] rounded-lg my-4 mx-2 modal-content">
	<div class="flex flex-col md:flex-row w-full p-8 md:space-x-4">
		<div class=" w-full dark:text-gray-900 overflow-y-scroll scrollbar-hidden">
			<form
				on:submit|preventDefault={() => {
					handleConfirm();
				}}
			>
				<!-- Letter type  -->
				<div class="flex w-full">
					<div class="w-2/3 mr-6">
						<div class="mb-2 text-sm">Letter Type</div>
						<div class="flex items-center">
							<select
								required
								bind:value={type}
								class="flex-1 rounded-md px-2 h-[44px] bg-transparent"
								style="border: 1px solid #0000004D"
							>
								{#each letters as leaveType}
									<option value={leaveType}>{leaveType}</option>
								{/each}
							</select>
						</div>
					</div>
					{#if type === 'Salary Certificate'}
						<div class="flex-1">
							<div class="mb-2 text-sm">Language</div>
							<div class="flex items-center">
								<select
									required
									bind:value={language}
									class="flex-1 rounded-md px-2 h-[44px] bg-transparent"
									style="border: 1px solid #0000004D"
								>
									{#each ['English', 'Arabic'] as lang}
										<option value={lang}>{lang}</option>
									{/each}
								</select>
							</div>
						</div>
					{/if}
				</div>

				{#if !type.includes('Golden')}
					<!-- Addressee -->
					<div class="mt-4 mb-2 text-sm">Addressee's Name</div>
					<Textfield required variant="outlined" bind:value={addressee} class="w-full" />

					<!-- Purpose  -->
					<div class="mt-4 mb-2 text-sm">Purpose of Request</div>
					<Textfield textarea required variant="outlined" bind:value={purpose} class="w-full" />
				{/if}
				<!-- Footer -->
				<div class="flex mt-8 justify-end">
					<button
						class="py-1 px-12 rounded-lg border border-black/opacity-3 text-black/opacity-60 text-sm dark:text-white"
						on:click={() => {
							// show = false;
							dispatch('cancel');
						}}>Cancel</button
					>
					<button class="py-1 px-12 ml-6 text-white bg-[#1595F4] rounded-lg text-sm" type="submit"
						>Confirm</button
					>
				</div>
			</form>
		</div>
	</div>
</div>

<!-- </Modal> -->

<style>
	.modal-content {
		animation: scaleUp 0.5s ease-out forwards;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.85);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
